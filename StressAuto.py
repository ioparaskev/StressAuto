import subprocess
import re
import time
import logging
import os
import signal
import progress_bar
import argparse

processes = []


def remove_multiple_strings(words, text):
    """
    :param words: list or tuple of words
    :param text: string
    :return: string
    """
    final_text = []
    to_replace = dict([(x, '') for x in words])
    # to_replace = {"condition1": "", "condition2": "text"}

    # use these three lines to do the replacement
    replace_escaped = dict((re.escape(k), v)
                           for k, v in to_replace.iteritems())
    pattern = re.compile("|".join(replace_escaped.keys()))
    for sentence in text:
        final_text.append(pattern.sub(
            lambda m: replace_escaped[re.escape(m.group(0))], sentence))
    return final_text


def kill_stack_processes(proc_stack):
    for process in proc_stack:
        process.kill()


class DebugLogPrint():
    """
        A class that either prints/logs/both/supress messages
        Replaces print and log calls
    """
    choices = ''
    log_path = ''

    def __set_choice__(self, choice):
        if choice:
            if choice == 'debug':
                self.choices = ('print', 'log')
            else:
                self.choices = (choice,)

    def __init__(self, print_choice=choices, log_path=''):
        if print_choice not in ('', 'print', 'log', 'debug'):
            raise NotImplementedError('This choices is not supported!')
        self.__set_choice__(print_choice)
        self.log_file_path = '{0}/debug.log'.format(log_path)

        logging.basicConfig(filename=self.log_file_path, level=logging.DEBUG)

    @staticmethod
    def dprint(message):
        print(message)

    @staticmethod
    def dlog(message, level):
        if level == 'DEBUG':
            logging.debug(message)
        else:
            logging.info(message) \
                if level == 'INFO' else logging.warning(message)

    def debuglogprint(self, message, level='INFO'):
        if self.choices:
            for choice in self.choices:
                self.dprint(message) if choice == 'print' \
                    else self.dlog(message, level)
        else:
            pass


class TopGrep():
    """
        Runs a top and greps the result
        We call two lines top, because -n 1 always returns a cached result
    """
    top_configuration = ['top', '-n', '2' '-b']
    grep = ['grep']

    def __init__(self, process_name, limit_lines_before=None, exclude=None):
        if limit_lines_before:
            self.grep.extend(('-B', limit_lines_before))

        if exclude:
            self.grep.extend(('-v', '\'', exclude, '\''))

        if process_name not in self.grep:
            self.grep.append(process_name)

    def get_configuration(self):
        return self.top_configuration, self.grep

    def run(self):
        topconf, grepconf = self.get_configuration()

        top = subprocess.Popen(topconf, stdout=subprocess.PIPE)
        topgrep = subprocess.Popen(grepconf, stdin=top.stdout,
                                   stdout=subprocess.PIPE)

        return topgrep

    @staticmethod
    def get_clear_percent(top_strip):
        clear_percent = (''.join(x for x in top_strip
                                 if (x.isdigit() or x == '.')))
        return clear_percent

    def get_cpuload(self, top_grep_cpu_proc):
        return self.get_clear_percent(
            top_strip=top_grep_cpu_proc.stdout.readlines()[1].split()[1])


class SubProc():
    """
        Process configuration:
        location : location string
        process_name : process name
        switches : { switch_name : (enabled, switch_flag, value) }
    """
    process_configuration = {'location': '',
                             'process_name': '',
                             'switches': {}}
    __process__ = None

    def __init__(self, process_name, location=None, switches=None):
        self.process_configuration['process_name'] = process_name
        self.__set_location__(location)
        self.process_configuration['switches'] = switches

    def __set_location__(self, location=None):
        self.process_configuration['location'] = location if location else ''

    def get_location(self):
        return self.process_configuration['location']

    def __enable_process_switches__(self, switch_names):
        for name in switch_names:
            try:
                self.process_configuration['switches'][name][0] = True
            except ValueError:
                raise ValueError('No such switch exists!')

    def __set_switch_value__(self, switch_name, value):
        try:
            self.process_configuration['switches'][switch_name][2] = str(value)
        except ValueError:
            raise ValueError('Error in setting switch value!')
        except KeyError:
            raise ValueError('No such switch exists!')

    # todo change active switching to ommit value needless flags
    def get_active_switches(self):
        active_switches = []
        for switch in self.process_configuration['switches'].keys():
            if self.process_configuration['switches'][switch][0]:
                active_switches.extend(
                    (self.process_configuration['switches'][switch][1],
                     self.process_configuration['switches'][switch][2]))
        return tuple(x for x in active_switches if x)

    def get_absolute_program_location(self):
        if self.process_configuration['location'] is 'global':
            # app is installed on system
            return self.process_configuration['process_name']

        # if path append path, else ./ local run
        path = self.process_configuration['location'] \
            if self.process_configuration['location'] else '.'
        return tuple(['{0}/{1}'.format(path,
                                       self.process_configuration[
                                           'process_name'
                                       ])])

    # todo add configuration checking first
    def run(self):
        prog = self.get_absolute_program_location()
        active_switches = self.get_active_switches()
        print(prog + active_switches)
        self.__process__ = subprocess.Popen(prog + active_switches,
                                            stdout=subprocess.PIPE)
        return self.__process__

    def kill(self, verbose=None):
        if verbose:
            print('Killing {0} process with pid {1}'.
                  format(self.process_configuration['process_name'],
                         self.__process__.pid))
        self.__process__.kill()


class Stress(SubProc):
    stress_configuration = {'location': './stress'}
    # todo should not use '' because of conflict with conf checking
    switches = {'verbose': [True, '-v', ''],
                'quiet': [None, '-q', ''],
                'dry': [None, '-n', ''],
                'timeout': [None, '-t', None],
                'cpu': [None, '-c', None],
                'io': [None, '-i', None],
                'vm': [None, '-m', None],
                'hdd': [None, '-d', None]}
    __process__ = None

    def __init__(self, process_name='stress', location=None, switches=None):
        SubProc.__init__(self, process_name, location,
                         switches=switches if switches else self.switches)


class CpuLimit(SubProc):
    __process__ = None
    switches = dict(pid=[True, '-p', None], exe=[None, '-e', None],
                    path=[None, '-P', None], limit=[True, '-l', '1'],
                    lazy=[True, '-z', ''], verbose=[True, '-v', ''])

    def __init__(self, process_name='cpulimit', location=None, switches=None):
        SubProc.__init__(self, process_name, location,
                         switches=switches if switches else self.switches)

    def set_cpulimit_pid_limit(self, pid=None, limit=1):
        SubProc.__set_switch_value__(self, 'pid', pid)
        SubProc.__set_switch_value__(self, 'limit', limit)

    def get_cpu_limit_configuration(self):
        return self.switches


class LimitedStress(object):
    __subprocess_stack__ = []
    __tool_location__ = dict
    __limit__ = 1
    __cpulimit_limit__ = 1
    __timeout__ = None
    __old_load__ = __new_load__ = None
    stress_types = None
    workers = 1
    topgrep = None

    def __init__(self, stress_types=('cpu',), limit=1, timeout=None,
                 tool_location=dict):
        self.__tool_location__ = tool_location
        self.__limit__ = self.__cpulimit_limit__ = limit
        self.__timeout__ = timeout
        self.topgrep = TopGrep('Cpu')
        self.stress_types = stress_types

    @staticmethod
    def get_stack():
        global processes
        return processes

    def add_pid_to_stack(self, pid):
        if pid not in self.get_stack():
            global processes
            processes.append(pid)

    def add_process_to_stack(self, proc):
        self.__subprocess_stack__.append(proc)

    def get_location(self, tool):
        return self.__tool_location__.get(tool, '')

    def run_stress(self):
        stress = Stress(location=self.get_location('stress'))
        stress.__enable_process_switches__(self.stress_types)
        for stype in self.stress_types:
            stress.__set_switch_value__(stype, self.workers)

        stress_run = stress.run()
        self.add_process_to_stack(stress)
        return stress_run

    @staticmethod
    def get_stress_pid(stress_run, workers_count=1):
        total_count = 0
        matches = []
        while total_count < workers_count:
            output = stress_run.stdout.readline()
            if re.search('\[[0-9]*\]?.forked', output):
                total_count += 1
                matches.append(re.search('\[[0-9]*\]?.forked', output).group())
        pid = (x.strip()
               for x in remove_multiple_strings(('[', ']', 'forked'), matches))
        return pid

    def fork_to_cpulimit(self, pid):
        cpulimit = CpuLimit()
        cpulimit.set_cpulimit_pid_limit(pid=pid, limit=self.__cpulimit_limit__)
        cpulimit.run()
        self.add_process_to_stack(cpulimit)
        self.add_pid_to_stack(pid)

    def limit_pid(self, stress_run):
        pids_forked = self.get_stress_pid(stress_run)
        for pid in pids_forked:
            global processes
            if pid not in processes:
                self.fork_to_cpulimit(pid)
            else:
                raise RuntimeError('Trying to fork pid '
                                   'that is already forked!')

    def stress(self):
        self.update_load('old')
        stress_run = self.run_stress()
        self.add_process_to_stack(stress_run)
        # find the pid that stress forks and limit it
        self.limit_pid(stress_run)
        self.update_load('new')

    def update_load(self, load_choice):
        # time.sleep(1)
        load = self.get_load(self.topgrep)
        if load_choice == 'new':
            self.__new_load__ = load
        else:
            self.__old_load__ = load

    @staticmethod
    def get_load(tgrep):
        tgrep_proc = tgrep.run()
        return float(tgrep.get_cpuload(tgrep_proc))

    def stabilization_check(self, topgrep):
        stabilize_msg = 'Waiting to stabilize load'
        progress_bar.progress_bar(text=stabilize_msg,
                                  toolbar_width=20)
        progress_bar.progress_bar(text='.' * len(stabilize_msg),
                                  placeholder='.',
                                  toolbar_width=20,
                                  delimiters=(' ', ' '))
        load = self.get_load(topgrep)
        print('\nTotal load: {0}'.format(load))
        return load

    def kill_normal_processes(self):
        kill_stack_processes(self.__subprocess_stack__)

    @staticmethod
    def kill_forked_processes():
        global processes
        for fork_process in processes:
            print('Killing fork process with pid {0}'.format(fork_process))
            os.kill(int(fork_process), signal.SIGKILL)

    def kill_everything(self):
        print('Killing everything')
        self.kill_normal_processes()
        self.kill_forked_processes()

    def timeout_sleep(self):
        print('Timeout is on\nSleeping {0} seconds'
              .format(self.__timeout__))
        time.sleep(self.__timeout__)

    @property
    def cpulimit_limit(self):
        return self.__cpulimit_limit__

    @cpulimit_limit.setter
    def cpulimit_limit(self, new_value):
        self.__cpulimit_limit__ = 100 if new_value > 100 else new_value

    @property
    def limits(self):
        return self.workers, self.cpulimit_limit

    @limits.setter
    def limits(self, value):
        self.cpulimit_limit = value
        #we need to spawn more workers to make it faster
        self.workers = int(value / 100) if value > 100 else 1

    def calculate_velocity(self):
        """
            Calculate the last stress percentage velocity
        """
        if self.__new_load__ and self.__old_load__:
            velocity = self.__new_load__ - self.__old_load__
        else:
            velocity = None
        return velocity

    def adjust_velocity(self, current_velocity):
        """
            Predict the new velocity to reach the limit
            Calculate the new limit based on the wanted and current velocity
        """
        if current_velocity:
            wanted_velocity = self.__limit__ - self.__new_load__
            new_limit = int((wanted_velocity/current_velocity)*self.__limit__)
            print(current_velocity, new_limit, wanted_velocity)
        else:
            new_limit = 100
        if new_limit < 0:
            raise ValueError('New limit is < 0\nWe should exit')
        self.limits = new_limit

    def run_and_keep_the_limit(self):
        while self.get_load(self.topgrep) + 2 < self.__limit__:
            print('Cpu load is currently at {0}'.
                  format(self.get_load(self.topgrep)))
            self.adjust_velocity(current_velocity=self.calculate_velocity())
            try:
                self.stress()
            except ValueError:
                break
        else:
            print('Cpu load is currently at {0}'.
                  format(self.get_load(self.topgrep)))
            self.stabilization_check(self.topgrep)

        if self.__timeout__:
            self.timeout_sleep()
        print('Target achieved')
        self.kill_everything()


def location_crafter(*args):
    tools = ('stress', 'cpulimit')
    __locations__ = dict()

    for count, location in enumerate(args):
        __locations__[tools[count]] = location

    return __locations__


def args_crafter():
    global parser
    parser = argparse.ArgumentParser(prog='StressAuto',
                                     description='Simple stress tool wrapper',
                                     usage='%(prog)s [options]')
    parser.add_argument('-l', '--limit', help='Limit of load to reach',
                        type=int, required=True)
    parser.add_argument('-t', '--timeout', help='Seconds after reaching '
                                                'target to quit',
                        type=int, default=0)
    parser.add_argument('-sl', '--slocation', help='Absolute path to '
                                                   'stress tool location',
                        default='', type=str)
    parser.add_argument('-cl', '--clocation', metavar='cpulimit Location',
                        help='Absolute path to cpulimit location',
                        default='', type=str)
    parser.add_argument('-st', '--stype', help='Type of stress c(pu) / hd(d)',
                        default='cpu', choices=('cpu', 'c', 'hdd', 'hd'))


if __name__ == '__main__':
    args_crafter()

    args_parse = parser.parse_args()

    locations = location_crafter(args_parse.slocation, args_parse.clocation)
    #todo add multiple types as tuple
    lstress = LimitedStress(('cpu',),
                            limit=args_parse.limit, timeout=args_parse.timeout,
                            tool_location=locations)

    lstress.run_and_keep_the_limit()






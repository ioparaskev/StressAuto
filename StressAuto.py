__author__ = 'John Paraskevopoulos'

import subprocess
import re
import time
import sys
import os
import signal
import progress_bar

processes = []


def remove_multiple_strings(words, in_text):
    """
    :param words: list or tuple of words
    :param in_text: string
    :return: string
    """

    to_replace = dict([(x, '') for x in words])
    # to_replace = {"condition1": "", "condition2": "text"}

    # use these three lines to do the replacement
    replace_escaped = dict((re.escape(k), v) for k, v in to_replace.iteritems())
    pattern = re.compile("|".join(replace_escaped.keys()))
    final_text = pattern.sub(lambda m: replace_escaped[re.escape(m.group(0))],
                             in_text)
    return final_text


def kill_stack_processes(proc_stack):
    for process in proc_stack:
        process.kill()


class SubProc():
    """
        Process configuration:
        location : location string
        process_name : process name
        switches : { switch_name : (enabled, switch_flag, value }
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
        return tuple(active_switches)

    def get_absolute_program_location(self):
        if self.process_configuration['location'] is 'global':
            #app is installed on system
            return self.process_configuration['process_name']

        #if path append path, else ./ local run
        path = self.process_configuration['location'] \
            if self.process_configuration['location'] else '.'
        return tuple(['{0}/{1}'.format(path,
                                       self.process_configuration[
                                           'process_name'
                                       ])])

    #todo add configuration checking first
    def run(self):
        prog = self.get_absolute_program_location()
        active_switches = self.get_active_switches()
        self.__process__ = subprocess.Popen(prog + active_switches,
                                            stdout=subprocess.PIPE)
        return self.__process__

    def kill(self, verbose=None):
        if verbose:
            print('Killing {0} process with pid {`}'.
                  format(self.process_configuration['process_name'],
                         self.__process__.pid))
        self.__process__.kill()


class Stress:
    stress_configuration = ['./stress']
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

    def __init__(self, stress_location=''):
        self.stress_location = stress_location
        self.__set_stress_basic__()

    def get_stress_configuration(self):
        return self.stress_configuration

    def __set_stress_basic__(self, stress_location=''):
        if stress_location:
            absolute_path = stress_location + \
                            self.get_stress_configuration()[0].strip('.\\')
            self.stress_configuration[0] = absolute_path
        self.stress_configuration.append('-v')
        # if self.timeout:
        #     self.stress_configuration.extend(('-t', self.timeout))

    def set_stress_configuration(self, cpu_workers=None, hdd_workers=None,
                                 io_workers=None):
        switches = {'-c': cpu_workers, '-d': hdd_workers, '-i': io_workers}
        for x in switches.keys():
            if switches[x]:
                self.stress_configuration.extend((x, str(switches[x])))

    def run(self):
        process = subprocess.Popen(self.get_stress_configuration(),
                                   stdout=subprocess.PIPE)
        self.__process__ = process
        return process

    def kill(self):
        print('Killing stress process with pid {}'.format(self.__process__.pid))
        self.__process__.kill()


class CpuLimit(SubProc):
    __process__ = None
    switches = {'pid': [True, '-p', None],
                'exe': [None, '-e', None],
                'path': [None, '-P', None],
                'limit': [True, '-l', '1'],
                'lazy': [True, '-z', ''],
                'verbose': [True, '-v', '']
    }

    def __init__(self, process_name='cpulimit', location=None, switches=None):
        SubProc.__init__(self, process_name, location,
                         switches=switches if switches else self.switches)

    def set_cpulimit_pid_limit(self, pid=None, limit=1):
        SubProc.__set_switch_value__(self, 'pid', pid)
        SubProc.__set_switch_value__(self, 'limit', limit)

    def get_cpu_limit_configuration(self):
        return self.switches


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

    def get_load(self, top_grep_cpu_proc):
        split_stdout = top_grep_cpu_proc.stdout.readlines()[1].split(' ')
        cpuload = float(split_stdout[split_stdout.index('us,') - 1])
        return cpuload


class LimitedStress():
    __subprocess_stack__ = []
    __tool_location__ = {}
    __limit__ = 1

    def __init__(self, limit=1, timeout=None, tool_location={}):
        self.__tool_location__ = tool_location
        self.__limit__ = limit

    def get_stack(self):
        global processes
        return processes

    def add_pid_to_stack(self, pid):
        if pid not in self.get_stack():
            global processes
            processes.append(pid)

    def add_process_to_stack(self, proc):
        self.__subprocess_stack__.append(proc)

    def run_stress(self):
        stress = Stress()
        stress.set_stress_configuration(cpu_workers=1)
        stress_run = stress.run()
        self.add_process_to_stack(stress)

        return stress_run

    @staticmethod
    def get_stress_pid(stress_output, stress_run):
        while not re.search('\[[0-9]*\]?.forked', stress_output):
            stress_output = stress_run.stdout.readline()
        pid = remove_multiple_strings(('[', ']', 'forked'),
                                      re.search('\[[0-9]*\]?.forked',
                                                stress_output).group()).strip()
        return pid

    def fork_to_cpulimit(self, pid):
        cpulimit = CpuLimit()
        cpulimit.set_cpulimit_pid_limit(pid=pid, limit=self.__limit__)
        # cpulimit.set_cpu_limit_configuration(pid=pid, limit=self.__limit__)
        cpulimit.run()
        self.add_process_to_stack(cpulimit)
        self.add_pid_to_stack(pid)

    def stress(self):
        stress_run = self.run_stress()
        self.add_process_to_stack(stress_run)
        stress_output = stress_run.stdout.readline()
        # find the pid that stress forks
        pid = self.get_stress_pid(stress_output, stress_run)
        global processes
        if pid not in processes:
            self.fork_to_cpulimit(pid)
        else:
            raise RuntimeError('Trying to fork pid that is already forked!')

    @staticmethod
    def get_load(tgrep):
        tgrep_proc = tgrep.run()
        return tgrep.get_load(tgrep_proc)

    def stabilization_sleep(self, topgrep):
        print('Waiting to stabilize load')
        stabilize_msg = 'Waiting to stabilize load'
        progress_bar.progress_bar(text=stabilize_msg,
                                  toolbar_width=20)
        progress_bar.progress_bar(text='.'*len(stabilize_msg), placeholder='.',
                                  toolbar_width=20,
                                  delimiters=(' ', ' '))
        load = self.get_load(topgrep)
        print('\nTotal load: {}'.format(load))
        return load

    def kill_normal_processes(self):
        kill_stack_processes(self.__subprocess_stack__)

    @staticmethod
    def kill_forked_processes():
        global processes
        for fork_process in processes:
            print('Killing fork process with pid {}'.format(fork_process))
            os.kill(int(fork_process), signal.SIGKILL)

    def kill_everything(self):
        print('Killing everything')
        self.kill_normal_processes()
        self.kill_forked_processes()

    def run_and_keep_the_limit(self):
        tgrep = TopGrep('Cpu')

        while self.get_load(tgrep) + 10 < self.__limit__:
            print('Cpu load is currently at {}'.format(self.get_load(tgrep)))
            self.stress()
            time.sleep(2)
        else:
            if self.stabilization_sleep(tgrep) + 5 < self.__limit__:
                self.run_and_keep_the_limit()
            else:
                print('Target achieved')
                self.kill_everything()


if __name__ == '__main__':
    lstress = LimitedStress(60)
    # LimitedStress(type=cpu, limit=blah, timeout=30,
    # tool_location={stress='global', cpulimit='global'})
    lstress.run_and_keep_the_limit()






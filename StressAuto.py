__author__ = 'John Paraskevopoulos'

import subprocess
import re
import time
import sys
import os
import signal

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
    final_text = pattern.sub(lambda m: replace_escaped[re.escape(m.group(0))], in_text)
    return final_text


def kill_stack_processes(proc_stack):
    for process in proc_stack:
        process.kill()


class SubProc():
    process_configuration = []
    __process__ = None

    def __init__(self, process_name, location=None):
        self.__set_location__(location, process_name)
        self.__set__runswitches__()

    def __set_location__(self, process_name, location=None):
        if location:
            self.process_configuration.append(location + process_name if location else './{}'.format(process_name))

    def __set__runswitches__(self):


class Stress:
    stress_configuration = ['./stress']
    __process__ = None

    def __init__(self, stress_location=''):
        self.stress_location = stress_location
        self.__set_stress_basic__()

    def get_stress_configuration(self):
        return self.stress_configuration

    def __set_stress_basic__(self, stress_location=''):
        if stress_location:
            absolute_path = stress_location + self.get_stress_configuration()[0].strip('.\\')
            self.stress_configuration[0] = absolute_path
        self.stress_configuration.append('-v')
        # if self.timeout:
        #     self.stress_configuration.extend(('-t', self.timeout))

    def set_stress_configuration(self, cpu_workers=None, hdd_workers=None, io_workers=None):
        switches = {'-c': cpu_workers, '-d': hdd_workers, '-i': io_workers}
        for x in switches.keys():
            if switches[x]:
                self.stress_configuration.extend((x, str(switches[x])))

    def run(self):
        # print(self.get_stress_configuration())
        process = subprocess.Popen(self.get_stress_configuration(), stdout=subprocess.PIPE)
        self.__process__ = process
        return process

    def kill(self):
        print('Killing stress process with pid {}'.format(self.__process__.pid))
        self.__process__.kill()


class CpuLimit:
    cpu_limit_configuration = ['./cpulimit']
    __process__ = None

    def set_cpu_limit_configuration(self, pid=None, limit=1, cpu_limit_location=None):
        if cpu_limit_location:
            absolute_path = cpu_limit_location + self.cpu_limit_configuration[0].strip('.\\')
            self.cpu_limit_configuration[0] = absolute_path
        self.cpu_limit_configuration.extend(('-l', str(limit), '-p', str(pid)))

    def get_cpu_limit_configuration(self):
        return self.cpu_limit_configuration

    def run(self):
        # print(self.get_cpu_limit_configuration())
        process = subprocess.Popen(self.get_cpu_limit_configuration(), stdout=subprocess.PIPE)
        self.__process__ = process
        print(self.__process__.pid)
        return process

    def kill(self):
        print('Killing process with pid {}'.format(self.__process__.pid))
        self.__process__.kill()


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
        topgrep = subprocess.Popen(grepconf, stdin=top.stdout, stdout=subprocess.PIPE)

        return topgrep

    def get_load(self, top_grep_cpu_proc):
        split_stdout = top_grep_cpu_proc.stdout.readlines()[1].split(' ')
        cpuload = float(split_stdout[split_stdout.index('us,') - 1])
        return cpuload


class LimitedStress():
    __subprocess_stack__ = []
    __tool_location__ = {}
    __limit__ = 1

    def __init__(self, limit=1, timeout=None, tool_location=None):
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
        stress.set_stress_configuration(cpu_workers=1, stress_lo)
        stress_run = stress.run()
        self.add_process_to_stack(stress)

        return stress_run

    def get_stress_pid(self, stress_output, stress_run):
        while not re.search('\[[0-9]*\]?.forked', stress_output):
            stress_output = stress_run.stdout.readline()
        pid = remove_multiple_strings(('[', ']', 'forked'),
                                      re.search('\[[0-9]*\]?.forked', stress_output).group()).strip()
        return pid

    def fork_to_cpulimit(self, pid):
        cpulimit = CpuLimit()
        cpulimit.set_cpu_limit_configuration(pid=pid, limit=self.__limit__,
                                             cpu_limit_location=self.__tool_location__.get('cpulimit', ''))
        cpulimit.run()
        self.add_process_to_stack(cpulimit)
        self.add_pid_to_stack(pid)

    def stress(self):
        stress_run = self.run_stress()
        self.add_process_to_stack(stress_run)
        stress_output = stress_run.stdout.readline()
        #find the pid that stress forks
        pid = self.get_stress_pid(stress_output, stress_run)
        global processes
        if pid not in processes:
            self.fork_to_cpulimit(pid)
        else:
            raise RuntimeError('Trying to fork pid that is already forked!')

    def get_load(self, tgrep):
        tgrep_proc = tgrep.run()
        return tgrep.get_load(tgrep_proc)

    def stabilization_sleep(self, topgrep):
        print('Waiting to stabilize load')
        for x in range(6):
            sys.stdout.write('.')
            time.sleep(1)
            sys.stdout.write('.')
        load = self.get_load(topgrep)
        print('\nTotal load: {}'.format(load))
        return load

    def kill_normal_processes(self):
        kill_stack_processes(self.__subprocess_stack__)

    def kill_forked_processes(self):
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
    lstress.run_and_keep_the_limit()






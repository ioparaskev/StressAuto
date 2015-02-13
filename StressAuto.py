__author__ = 'jparaske'

import subprocess


class Stress:
    stress_configuration = ['./stress']

    def __init__(self, timeout=None, stress_location=''):
        self.timeout = timeout
        self.stress_location = stress_location
        self.__set_stress_basic__()

    def __set_stress_basic__(self):
        absolute_path = self.stress_location + self.stress_configuration[0]
        self.stress_configuration[0] = absolute_path
        self.stress_configuration.append('-v')
        if self.timeout:
            self.stress_configuration.extend(('-t', self.timeout))

    def set_stress_configuration(self, cpu_workers=None, hdd_workers=None, io_workers=None):
        switches = {'-c': cpu_workers, '-d': hdd_workers, '-i': io_workers}
        for x in switches.keys():
            if switches[x]:
                self.stress_configuration.extend((x, str(switches[x])))

    def get_stress_configuration(self):
        return self.stress_configuration

    def run(self):
        # process = subprocess.Popen(' '.join(self.get_stress_configuration()), shell=True, stdout=subprocess.PIPE)
        process = subprocess.Popen(self.get_stress_configuration(), stdout=subprocess.PIPE)
        return process


class CpuLimit:

    def __init__(self):

        pass


class LimitedStress(object, Stress):
    stack_of_processes = []

    def __init__(self, limit=1, timeout=None, stress_location=''):
        Stress.__init__(self, timeout, stress_location)
        super(LimitedStress, self).__init__()

    def get_stack(self):
        return self.stack_of_processes

    def add_to_stack(self, pid):
        if pid not in self.get_stack():
            self.stack_of_processes.append(pid)


    # def limit(self, percent=1,):
class topProcess:
    top_configuration = ['top', '-n', '1', '-b']
    topgrep = ['grep']

    def __init__(self, process_name, limit_lines_before=None, exclude=None):
        if limit_lines_before:
            self.topgrep.extend(('-B', limit_lines_before))

        if exclude:
            self.topgrep.extend(('-v', '\'', exclude, '\''))

        self.topgrep.append(process_name)

    def get_configuration(self):
        return self.top_configuration, self.topgrep

    def run(self):
        topconf, grepconf = self.get_configuration()

        top = subprocess.Popen(topconf, stdout=subprocess.PIPE)
        topgrep = subprocess.Popen(grepconf, stdin=top.stdout, stdout=subprocess.PIPE)

        return topgrep


if __name__ == '__main__':
    # cpu = LimitedStress()
    # cpu_workers = 3
    # cpu.set_stress_configuration(cpu_workers=cpu_workers)
    # a = cpu.run()

    cpu_limit = 50
    # print(top_cpu.stdout.readlines())
    import time
    # print(top_cpu.stdout.readlines()[0].split(''))
    while True:
        top_cpu = topProcess('Cpu').run()
        cpu_load = top_cpu.stdout.readlines()[0].split(' ')[1]
        if float(cpu_load) > cpu_limit:
            break
        else:
            LimitedStress().run()
        time.sleep(2)


    # print(topgrep.stdout.readlines())
    # # for i in xrange(2, 7):
    # from itertools import islice
    # with open(a.stdout.read()) as myfile:
    #     head = list(islice(myfile, 0, 7, 2))
    # print(head)

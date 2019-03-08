import sys
import os
import subprocess
import time

CURRENT_PATH = os.getcwd() + os.path.sep
SAMPLE_PATH = os.path.join(CURRENT_PATH, 'data', 'samples')


# 编译，错误信息输出到error.txt中
def compile(filename):
    name, pro = filename.split("/")[-1].split('.')
    compiler = {'c': 'gcc ', 'cpp': 'g++ '}
    os.system(
        compiler.get(pro) + filename + ' -o ' + name + ' > error.txt 2>&1')
    if os.path.exists(name + '.exe'):
        return True
    else:
        return False


# 获取题目输入
def get_samples(n):
    with open(SAMPLE_PATH + str(n) + '_input.txt', "r") as inputs_file:
        inputs = []

        row_num = inputs_file.readline()
        while row_num != '' and row_num != '\n' and row_num is not None:
            input = ""
            for i in range(int(row_num)):
                input += inputs_file.readline()
            inputs.append(input)

            row_num = inputs_file.readline()

    with open(SAMPLE_PATH + str(n) + '_output.txt', "r") as outputs_file:
        outputs = []

        row_num = outputs_file.readline()
        while row_num != '' and row_num != '\n' and row_num is not None:
            output = ""
            for i in range(int(row_num)):
                output += outputs_file.readline()
            outputs.append(output)

            row_num = outputs_file.readline()

    return inputs, outputs


def check(filename: str, n: int, time_limit: int, memory_limit: int) -> ([str], [int], [int]):
    '''

    :param filename: source file to be judged
    :param n: unique id of the problem
    :param time_limit: second
    :param memory_limit: kB
    :return:
    '''
    Status, Time, Memory = [], [], []
    if compile(filename):
        executable = CURRENT_PATH + filename.split('.')[0] + '.exe'
        inputs, outputs = get_samples(n)
        for i in range(len(inputs)):
            begin = time.perf_counter()
            try:
                ret = subprocess.run(
                    executable,
                    input=inputs[i],
                    stdout=subprocess.PIPE,
                    timeout=time_limit,
                    encoding='gbk')
                ret.check_returncode()
            except subprocess.TimeoutExpired:
                Status.append('Time Limit Exceeded')
            except subprocess.CalledProcessError:
                Status.append('Runtime Error')
            end = time.perf_counter()
            ans = [line.rstrip() for line in outputs[i].split("\n")]
            out = [line.rstrip() for line in ret.stdout.split("\n")]
            if ans != out:
                Status.append('Wrong Answer')
            else:
                Status.append('Accepted')
            Time.append(int(1000 * (end - begin)))  # 返回用时 ms
            Memory.append(memory_limit)
        os.remove(executable)
    else:
        Status.append('Compilation Error')
        Time.append(0)
        Memory.append(0)
    return Status, Time, Memory


if __name__ == '__main__':
    Status, Time, Memory = check('ghq.cpp', 1, 1000, 100000)
    print(Status)
    print(Time)
    print(Memory)

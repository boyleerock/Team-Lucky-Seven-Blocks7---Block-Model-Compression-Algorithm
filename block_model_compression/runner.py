import argparse
import sys
import os
import io
import subprocess
import time
import timeit
import tempfile
import typing
from operator import itemgetter

def get_header_info_of_file1(file1: io.IOBase, line: str, line_count: int, stderr) -> typing.List[int]:
    try:
        line = file1.readline()
        if line == "":
            print("Error: unexpected end of input on line {}".format(
                line_count),
                file=stderr)
            sys.exit(100)
    except OSError as err:
        print("Error: failed to read line {} ({})".format(
            line_count,
            err.strerror),
            file=stderr)
        sys.exit(200)
    except:
        print("Error: failed to read line {} ({})".format(
            line_count,
            sys.exc_info()[0]),
            file=stderr)
        sys.exit(300)
    return parse_line1_of_file1(line, line_count, stderr)

def parse_line1_of_file1(line: str, line_count: int, stderr) -> typing.List[int]:
    if line[0] != "#":
        print("Error: line {} expected '# x,y,z,px,py,pz' and instead found {}.".format(
            line_count,
            line),
            file=stderr)
        sys.exit(1)
    try:
        ints = [int(i) for i in line[1:].split(',')]
    except ValueError as err:
        print("line {}: {}Error: {}".format(
            line_count,
            line,
            err),
            file=stderr)
        sys.exit(1)
    if len(ints) != 6:
        print("line {}: {}Error: expecting line to be six integers of the format:".format(
            line_count,
            line),
            file=stderr)
        print("# <x_count>, <y_count>, <z_count>, <x_parent_size>, <y_parent_size>, <z_parent_size>",
            file=stderr)
        sys.exit(1)
    return ints

def read_next_line_of_input(file, line_count, stderr):
    try:
        while True:
            line = file.readline()
            line_count += 1
            if len(line) == 0:
                break
            elif line[0] == '#' or line[0] == '\n' or line[0] == '\r':
                # Ignore comment lines and blank lines
                continue
            else:
                break
    except OSError as err:
        print("Error: failed to read line {} ({})".format(
            line_count,
            err.strerror),
            file=stderr)
        sys.exit(200)
    except:
        print("Error: failed to read line {} ({})".format(
            line_count,
            sys.exc_info()[0]),
            file=stderr)
        sys.exit(300)
    return line, line_count

def file_format_error_and_exit(line: str, line_count: int, stderr):
    print("line {}: {}Error: expecting format '{}'".format(
        line_count,
        line,
        "x, y, z, sx, sy, sz, string"),
        file=stderr)
    sys.exit(1)

def parse_and_check_line_of_file1(x: int, y: int, z:int, line: str, line_count: int, stderr, domains: typing.Dict):
    last_comma = line.rfind(",")
    if last_comma == -1:
        file_format_error_and_exit(line, line_count, stderr)
    domain = line[last_comma+1:].strip("' \n\r")
    domains[domain] = domains.get(domain, 0) + 1
    try:
        ints = [int(i) for i in line[0:last_comma].split(',')]
    except ValueError as err:
        print("line {}: {}Error: {}".format(
            line_count,
            line,
            err),
            file=stderr)
        sys.exit(1)
    if ints[0] != x:
        print("line {}: {}Error: expected x index to be {} in format x,y,z,px,py,pz,string".format(
            line_count,
            line,
            x),
            file=stderr)
        sys.exit(1)
    if ints[1] != y:
        print("line {}: {}Error: expected y index to be {} in format x,y,z,px,py,pz,string".format(
            line_count,
            line,
            y),
            file=stderr)
        sys.exit(1)
    if ints[2] != z:
        print("line {}: {}Error: expected z index to be {} in format x,y,z,px,py,pz,string".format(
            line_count,
            line,
            z),
            file=stderr)
        sys.exit(1)
    if ints[3] != 1 or ints[4] != 1 or ints[5] != 1:
        print("line {}: {}Error: expecting unit sized blocks only".format(
            line_count,
            line),
            file=stderr)
        sys.exit(1)
    return ints[0], ints[1], ints[2], ints[3], ints[4], ints[5], domain

def parse_line(
    line: str,
    line_count: int,
    parent_size_x: int,
    parent_size_y: int,
    parent_size_z: int,
    stderr):
    last_comma = line.rfind(",")
    if last_comma == -1:
        file_format_error_and_exit(line, line_count, stderr)
    domain = line[last_comma+1:].strip("' \n\r")
    try:
        ints = [int(i) for i in line[0:last_comma].split(',')]
    except ValueError as err:
        print("line {}: {}Error: {}".format(
            line_count,
            line,
            err),
            file=stderr)
        sys.exit(1)
    if ints[3] < 0 or ints[4] < 0 or ints[5] < 0:
        print("line {}: {}Error: expecting positive block sizes only".format(
            line_count,
            line),
            file=stderr)
        sys.exit(1)
    if ints[3] > parent_size_x or ints[4] > parent_size_y or ints[5] > parent_size_z:
        print("line {}: {}Error: block is too large".format(
            line_count,
            line),
            file=stderr)
        sys.exit(1)
    return ints[0], ints[1], ints[2], ints[3], ints[4], ints[5], domain

parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog=
        "Tests a Python script or executable under the measurement rules of the\n"
        "Maptek Titan Block Model Compression Competition using the provided\n"
        "block model .csv file as input. The item under test is run in its own\n"
        "process with the input .csv file provided to it on standard input.\n"
        "Standard output from this process is then checked for correctness and\n"
        "block model equivalence to the input file. Upon successful completion\n"
        "this script returns with a zero exit status and the compression\n"
        "achieved will appear on standard output as a floating point number\n"
        "between 0 and 1 followed by a newline. (0 means no compression, 0.25\n"
        "means 25% compression ... so higher is better.)\n"
        "\n"
        "As soon as any error is encountered this script instead returns with\n"
        "a non-zero exit status and diagnostic information is returned on\n"
        "standard error. Note that if multiple errors are present in the output\n"
        "the diagnostic information is only going the report the first one.\n"
        "\n"
        "Additionally, optional argument -s will also measure the speed of the\n"
        "item under test. This will take slightly longer to run because the\n"
        "speed is measured relative to a separate process performing a straight\n"
        "copy of standard input to standard output, which is executed first.\n"
        "Upon successful completion the output and exit status is as before\n"
        "except that the measured speed will also appear on standard output,\n"
        "following the compression value, as a floating point number between\n"
        "0 and ~1 followed by a newline. (0.2 means five times slower than the\n"
        "direct copy, 1.0 means just as fast ... so higher is better.)\n"
        "\n"
        "Additionally, a -v option can be specified for more verbose output\n"
        "showing what this script is up to."
)
parser.add_argument(
    "path_to_item_under_test",
    metavar="<my_algorithm.py or my_algorithm.exe>",
    help="script or executable to run")
parser.add_argument(
    "path_to_block_model_input_csv",
    metavar="<input_block_model.csv>",
    help="input block model csv to pass to it on stdin")
parser.add_argument(
    "-s", 
    "--speed",
    help="output speed in addition to compression",
    action="store_true")
parser.add_argument(
    "-v",
    "--verbose",
    help="print additional output to see details and progress",
    action="store_true")
args = parser.parse_args()
strnull = open(os.devnull, 'w')
stdout = sys.stdout
stderr = sys.stderr
stdvout = sys.stderr if args.verbose else strnull

if not os.path.isfile(args.path_to_item_under_test):
    print("Script or execuitable not found at '{}'".format(
        args.path_to_item_under_test),
        file=stderr)
    sys.exit(10)
if not (
    args.path_to_item_under_test.endswith(".py") or
    args.path_to_item_under_test.endswith(".exe")):
    print("'{}' must be a Python (.py) or executable (.exe) file".format(
        args.path_to_item_under_test),
        file=stderr)
    sys.exit(11)
if not os.path.isfile(args.path_to_block_model_input_csv):
    print("Input block model file not found at '{}'".format(
        args.path_to_block_model_input_csv),
        file=stderr)
    sys.exit(12)

with tempfile.TemporaryDirectory() as tmpdir:
    if args.speed:
        print("Using temporary directory '{}'".format(tmpdir),file=stdvout)
        print("Measuring straight stdin to stdout speed...", file=stdvout)
        command = [
            "cmd.exe",
            "/c",
            r"std2std.exe",
            "<", args.path_to_block_model_input_csv,
            ">", "{}/out0.csv".format(tmpdir),
            "2>", "{}/err0.txt".format(tmpdir),
            ]
        print("...doing warm up run", file=stdvout)
        completed_process = subprocess.run(command)
        if completed_process.returncode != 0:
            print("Baseline speed measurement process failed", file=stderr)
            sys.exit(13)
        print("...done", file=stdvout)
        print("...doing timed run", file=stdvout)
        tic = timeit.default_timer()
        completed_process = subprocess.run(command)
        toc = timeit.default_timer()
        if completed_process.returncode != 0:
            print("Baseline speed measurement process failed", file=stderr)
            sys.exit(13)
        baseline_time = toc - tic
        print("...done in {:.3f}s".format(baseline_time), file=stdvout)
    print("Running the item under test...", file=stdvout)
    command_head = ["cmd.exe", "/c"]
    if args.path_to_item_under_test.endswith(".py"):
        command_body = [sys.executable, args.path_to_item_under_test]
    else:
        command_body = [args.path_to_item_under_test]
    command_tail = [
        "<", args.path_to_block_model_input_csv,
        ">", "{}/out.csv".format(tmpdir),
        "2>", "{}/err.txt".format(tmpdir)]
    command = command_head + command_body + command_tail
    print('..."{}"'.format(" ".join(command[0:-4])), file=stdvout)
    tic = timeit.default_timer()
    completed_process = subprocess.run(command)
    toc = timeit.default_timer()
    if completed_process.returncode != 0:
        print("Error: {} exited with exit status {}.".format(
            args.path_to_item_under_test,
            completed_process.returncode),
            file=stderr)
        print("Console showing stderr looks like...\n> {}".format(
            " ".join(command[:-4])),
            file=stderr)
        with open("{}/err.txt".format(tmpdir), "r") as errors:
            print(errors.read(), file=stderr)
        sys.exit(14)
    item_under_test_time = toc - tic
    print("...done in {:.3f}s".format(item_under_test_time), file=stdvout)
    print("Analysing the output of the item under test...", file=stdvout)
    with open(args.path_to_block_model_input_csv, "r") as file1, \
         open("{}/out.csv".format(tmpdir), "r") as file2:
        line_f1 = ""
        line_count_f1 = 1
        ints = get_header_info_of_file1(file1, line_f1, line_count_f1, stderr)
        x_count = ints[0]
        y_count = ints[1]
        z_count = ints[2]
        block_count_f1 = x_count * y_count * z_count
        parent_size_x = ints[3]
        parent_size_y = ints[4]
        parent_size_z = ints[5]
        print("...looking for {} blocks.".format(x_count * y_count * z_count),
            file=stdvout)
        # We now have sufficient info from file1 to start reading in the first
        # chunk of file2. A chunk is all the blocks in a parent_size_z run of
        # consecutive slices in z.
        line_count_f2 = 0
        line_f2, line_count_f2 = read_next_line_of_input(file2, line_count_f2, stderr)
        if line_f2 == "":
            print("Error: unexpected end of input on line {}".format(
                line_count_f2),
                file=stderr)
            sys.exit(100)
        line_count_f2_last_chunk_end = 0
        block_count_f2 = 0
        for z in range(0, z_count, parent_size_z):
            print("...reading chunk {} of {}".format(
                z // parent_size_z + 1, z_count // parent_size_z),
                file=stdvout)
            chunk_list = []
            while True:
                x2, y2, z2, xs2, ys2, zs2, domain = parse_line(
                    line_f2,
                    line_count_f2,
                    parent_size_x,
                    parent_size_y,
                    parent_size_z,
                    stderr)
                if z2 < z:
                    # This block is from an earlier chunk and we mandate chunkwise
                    # processing => format error.
                    print("{}: {}Error: block z value lies in an earlier chunk, expected before line {}.".format(
                        line_count_f2,
                        line_f2,
                        line_count_f2_last_chunk_end - 1),
                        file=stderr)
                    sys.exit(1)
                elif x2 // parent_size_x != (x2 + xs2 - 1) // parent_size_x:
                    print("{}: {}Error: block crosses a parent block boundary in the x direction.".format(
                        line_count_f2,
                        line_f2),
                        file=stderr)
                    sys.exit(1)
                elif y2 // parent_size_y != (y2 + ys2 - 1) // parent_size_y:
                    print("{}: {}Error: block crosses a parent block boundary in the y direction.".format(
                        line_count_f2,
                        line_f2),
                        file=stderr)
                    sys.exit(1)
                elif z2 // parent_size_z != (z2 + zs2 - 1) // parent_size_z:
                    print("{}: {}Error: block crosses a parent block boundary in the z direction.".format(
                        line_count_f2,
                        line_f2),
                        file=stderr)
                    sys.exit(1)
                elif z2 > z + parent_size_z - 1:
                    # This block is from the next chunk, so don't process it yet
                    # and assume we have come to the end of the current chunk.
                    line_count_f2_last_chunk_end = line_count_f2
                    break
                # Explode the block into sub-blocks and add each to the chunk list
                block_count_f2 += 1
                for sz in range(zs2):
                    for sy in range(ys2):
                        for sx in range(xs2):
                            chunk_list.append([x2+sx, y2+sy, z2+sz, domain, line_count_f2])
                # Now grab the next line and continue the loop
                line_f2, line_count_f2 = read_next_line_of_input(file2, line_count_f2, stderr)
                if line_f2 == "":
                    # We have reached the end of the file and now should process
                    # the last chunk.
                    break
            # Sort the data by x, y and z in that order:
            chunk_list.sort(key=itemgetter(2,1,0))
            # Now compare it line by line with file1 over the slice range z:z+zsf
            print("...checking chunk {} of {}".format(
                z // parent_size_z + 1, z_count // parent_size_z),
                file=stdvout)
            for e in chunk_list:
                line_f1, line_count_f1 = read_next_line_of_input(
                    file1,
                    line_count_f1,
                    stderr)
                if line_f1 == "":
                    print("Error: {} specifies more blocks than {} from line {} onwards.".format(
                        file2.name,
                        file1.name,
                        e[4]),
                        file=stderr)
                    sys.exit(1)
                x1, y1, z1, xs1, ys1, zs1, domain1 = parse_line(
                    line_f1,
                    line_count_f1,
                    1,
                    1,
                    1,
                    stderr)
                if e[0] != x1 or e[1] != y1 or e[2] != z1:
                    print("Error: block {},{},{} missing, duplicated or should appear earlier in the output.".format(
                        x1,
                        y1,
                        z1),
                        file=stderr)
                    sys.exit(1)
                if e[3] != domain1:
                    print("Error: block {},{},{},'{}' on line {} should be '{}'.".format(
                        x1,
                        y1,
                        z1,
                        e[3],
                        e[4],
                        domain1),
                        file=stderr)
                    sys.exit(1)
        print("...equivalence = 100%", file=stdvout)
        print("-----------", file=stdvout)
        compression = (block_count_f1 - block_count_f2) / block_count_f1
        print("Compression = {:6.2f}%  ({} blocks down from {} blocks)".format(
            compression*100,
            block_count_f2,
            block_count_f1), file=stdvout)
        if args.speed:
            speed = baseline_time / item_under_test_time
            print("      Speed = {:6.2f}%  ({:.0f} blocks per second, raw io is {:.0f})".format(
                speed*100,
                block_count_f1/item_under_test_time,
                block_count_f1/baseline_time),
                file=stdvout)
        print("-----------", file=stdvout)
        print("exit status is 0", file=stdvout)
        print("stdout is:", file=stdvout)
        # Print final results to stdout
        print("{}".format(compression), file=stdout)
        if args.speed:
            print("{}".format(speed), file=stdout)

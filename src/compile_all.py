import os

from generator.generator import generate

test_dir: str = 'test/' if os.path.exists('test/') else 'src/test/'

c_files = []
for root, dirs, files in os.walk(test_dir):
    for file in files:
        suffix = os.path.splitext(file)[1]
        if suffix == '.c':
            input_filename = test_dir + file
            print("compiling ", input_filename)
            output_filename = input_filename.split(".")[0] + ".ll"
            generate(input_filename, output_filename)

import os

files = sorted(f for f in os.listdir('.') if os.path.isfile(f))

with open('merged_output.txt', 'w') as out_file:
    for file_name in files:
        with open(file_name, 'r') as in_file:
            next(in_file)  # Skip the first line
            second_line = next(in_file).strip()  # Capture the second line to remove later
            rest_of_lines = in_file.readlines()[1:-2]  # Skip the last line too
            out_file.write(''.join(rest_of_lines) + '\n')

            # Remove second line from the content before merging
            with open(file_name, 'r') as ref_file:
                content = ref_file.readlines()
                del content[1]  # Remove second line
                ref_file.writelines(content)

            out_file.write(second_line + '\n')  

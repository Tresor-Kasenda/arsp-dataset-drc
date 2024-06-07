
# get the content of output.txt and get each first line of each block of text and sort them alphabetically and write them to a new file called sorted.txt
with open('output.txt', 'r', encoding='utf-8') as f_in:
    blocks = f_in.read().split('\n\n')  # split the input file into blocks
    first_lines = [block.split('\n')[0] for block in blocks]  # get the first line of each block

first_lines.sort()  # sort the lines alphabetically

with open('sorted.txt', 'w', encoding='utf-8') as f_out:
    for line in first_lines:
        f_out.write(line + '\n')  # write to the output file
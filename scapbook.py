from pprint import pprint

x = {
    'x': 'a',
    'y': 'c',
    'z': 'b',
}

for i, thing in enumerate(x.items()):
    letter = thing[0]
    other_letter = thing[1]
    print(letter, other_letter)
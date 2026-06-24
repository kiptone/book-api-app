import sys

sys.path.insert(0, r'C:\Users\Danila\Desktop\book-api')
mods = ['src.clients','src.sync','src.main','src.repositories','src.usecases','src.models']
for m in mods:
    try:
        __import__(m)
        print('OK', m)
    except Exception as e:
        print('ERR', m, e)

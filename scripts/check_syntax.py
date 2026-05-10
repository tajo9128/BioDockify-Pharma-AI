try:
    import api.main
    print('Import OK')
except ImportError:
    print('Import Error (Expected due to missing deps)')
except SyntaxError:
    print('SYNTAX ERROR IN CODE')
except Exception as e:
    print(f'Other Error: {e}')

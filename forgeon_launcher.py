"""Ponto de entrada do executável Windows e da verificação de empacotamento."""
import sys

if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--verificar-instalacao':
        from forgeon.packaging_check import check
        raise SystemExit(check(sys.argv[2]))
    from forgeon.__main__ import main
    raise SystemExit(main())

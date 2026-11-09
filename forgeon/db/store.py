from pathlib import Path
import sqlite3
from contextlib import contextmanager, closing
from datetime import datetime
import json
import os
import shutil
import tempfile

APP_ID = 1179797298
PROJECT = 'forgeon-studio-erp-2-new'
LATEST_SCHEMA = 3
DEFAULTS = {'filament_kg': '90', 'energy_kwh': '1', 'power_w': '150', 'machine_hour': '1',
            'fee_percent': '0', 'fee_fixed': '0', 'pricing_mode': 'margem', 'profit_percent': '30', 'sku_width': '5'}


def data_directory():
    base = Path(os.environ.get('LOCALAPPDATA', Path.home() / '.local' / 'share'))
    return base / 'ForgeonStudioERP2'


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        existed = self.path.exists() and self.path.stat().st_size > 0
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        if existed:
            try:
                self.validate(self.db)
                self.verify_schema(self.db)
                if self.db.execute("PRAGMA user_version").fetchone()[0]<LATEST_SCHEMA:
                    self.backup()
                    self.migrate(self.db)
            except Exception:
                self.db.close()
                raise
        else:
            self.db.executescript(Path(__file__).with_name('schema.sql').read_text(encoding='utf-8'))
            self.db.executemany('INSERT INTO settings VALUES(?,?)', DEFAULTS.items())
            self.db.commit()
            self.migrate(self.db)

    @staticmethod
    def validate(connection):
        if connection.execute('PRAGMA application_id').fetchone()[0] != APP_ID or connection.execute('PRAGMA user_version').fetchone()[0] not in (1,2,3):
            raise ValueError('Banco incompatível com FORGEON ERP 2.0 (projeto novo).')
        if connection.execute("SELECT value FROM meta WHERE key='project'").fetchone()[0] != PROJECT:
            raise ValueError('Identidade do banco incompatível.')
        if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or connection.execute('PRAGMA foreign_key_check').fetchone():
            raise ValueError('Falha de integridade do banco.')

    @staticmethod
    def migrate(connection,target=LATEST_SCHEMA):
        version=connection.execute('PRAGMA user_version').fetchone()[0]
        for next_version in range(version+1,target+1):
            try:
                script=Path(__file__).with_name(f'migration_v{next_version}.sql').read_text(encoding='utf-8')
                connection.executescript('BEGIN IMMEDIATE;\n'+script+'\nCOMMIT;')
            except Exception:
                connection.rollback()
                raise

    @staticmethod
    def verify_schema(connection):
        version=connection.execute('PRAGMA user_version').fetchone()[0]
        with closing(sqlite3.connect(':memory:')) as reference:
            reference.executescript(Path(__file__).with_name('schema.sql').read_text(encoding='utf-8'))
            if version>1:Store.migrate(reference,version)
            def definitions(conn):
                return {r[0]: ' '.join(r[1].split()).lower() for r in conn.execute("SELECT name,sql FROM sqlite_master WHERE type='table'")}
            if definitions(connection)!=definitions(reference) or connection.execute("SELECT 1 FROM sqlite_master WHERE type IN('trigger','view')").fetchone():
                raise ValueError('Esquema de backup não corresponde a este projeto.')

    def rows(self, sql, args=()):
        return [dict(r) for r in self.db.execute(sql, args)]

    def one(self, sql, args=()):
        r = self.db.execute(sql, args).fetchone()
        return dict(r) if r else None

    @contextmanager
    def transaction(self):
        if self.db.in_transaction:
            raise RuntimeError('Transação aninhada não permitida.')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def log(self, operation, detail):
        self.db.execute('INSERT INTO audit(operation,detail) VALUES(?,?)', (operation, json.dumps(detail, ensure_ascii=False)))

    def settings(self):
        return {r['key']: r['value'] for r in self.rows('SELECT * FROM settings')}

    def backup(self, target=None):
        if self.db.in_transaction:
            raise RuntimeError('Backup deve ocorrer fora de transações.')
        if target is None:
            folder = self.path.parent / 'backups'
            folder.mkdir(exist_ok=True)
            target = folder / f'forgeon2-{datetime.now():%Y%m%d-%H%M%S-%f}.sqlite3'
        target = Path(target)
        if target.resolve() == self.path.resolve() or target.exists():
            raise ValueError('Escolha um arquivo novo para o backup.')
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            with closing(sqlite3.connect(target)) as dest, dest:
                self.db.backup(dest)
                self.validate(dest)
        except Exception:
            target.unlink(missing_ok=True)
            raise
        return target

    def restore(self, source):
        source = Path(source).resolve()
        if source == self.path.resolve() or not source.is_file():
            raise ValueError('Escolha outro arquivo de backup existente.')
        if source.stat().st_size > 512 * 1024 * 1024:
            raise ValueError('Backup excede 512 MB.')
        # Copy to private staging first, validate and restore that same immutable snapshot.
        fd, staged = tempfile.mkstemp(dir=self.path.parent, suffix='.restore')
        os.close(fd)
        try:
            shutil.copyfile(source, staged)
            with closing(sqlite3.connect(staged)) as candidate:
                candidate.execute('PRAGMA trusted_schema=OFF')
                self.validate(candidate)
                self.verify_schema(candidate)
                self.migrate(candidate)
                self.validate(candidate)
                self.verify_schema(candidate)
                preserved = self.backup()
                candidate.backup(self.db)
            self.db.execute('PRAGMA foreign_keys=ON')
            with self.transaction():
                self.log('restauracao', {'preservado': preserved.name})
            return preserved
        finally:
            Path(staged).unlink(missing_ok=True)

    def close(self):
        self.db.close()

from pathlib import Path
from threading import Event
from PySide6.QtCore import QThread,Signal,QStandardPaths,Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QLabel,QTextBrowser,QPushButton,QProgressBar,QFileDialog,QHBoxLayout,QMessageBox)
from .widgets import Page
from .visual import GlassCard,ASSETS
from ..version import VERSION,HOTFIX,REPOSITORY
from ..business.updates import fetch_release,download_release


class UpdateTask(QThread):
    done=Signal(object);failed=Signal(str);progress=Signal(int,int)
    def __init__(self,release=None,destination=None,parent=None):
        super().__init__(parent);self.release=release;self.destination=destination;self.cancel=Event()
    def run(self):
        try:
            result=download_release(self.release,self.destination,self.progress.emit,self.cancel) if self.release else fetch_release()
            self.done.emit(result)
        except Exception as error:
            from urllib.error import URLError,HTTPError
            message='Não foi possível acessar o GitHub. Verifique sua conexão e tente novamente.' if isinstance(error,(URLError,TimeoutError,OSError)) else str(error)
            self.failed.emit(message)


class UpdatesPage(Page):
    def __init__(self,parent_window):
        super().__init__('Atualizações e novidades','Você escolhe quando consultar e baixar. O instalador nunca é executado automaticamente.')
        self.window=parent_window;self.release=None;self.task=None
        version=QLabel(f'VERSÃO INSTALADA  {VERSION}  /  {HOTFIX}');version.setObjectName('badge');self.layout.addWidget(version)
        self.check_button=self.button('Verificar atualizações',self.check,True)
        self.download_button=self.button('Baixar hotfix disponível',self.download);self.download_button.setEnabled(False)
        self.cancel_button=self.button('Cancelar download',self.cancel);self.cancel_button.setEnabled(False)
        card=GlassCard();self.state=QLabel('Nenhuma consulta foi feita. O histórico abaixo funciona sem internet.');self.state.setWordWrap(True);card.body.addWidget(self.state)
        self.progress=QProgressBar();self.progress.setRange(0,100);self.progress.hide();card.body.addWidget(self.progress)
        self.remote_notes=QTextBrowser();self.remote_notes.setMaximumHeight(180);self.remote_notes.hide();card.body.addWidget(self.remote_notes)
        self.layout.addWidget(card)
        self.notes=QTextBrowser();self.notes.setMarkdown((ASSETS/'CHANGELOG.md').read_text(encoding='utf-8'));self.layout.addWidget(self.notes,1)

    def busy(self,value):
        self.check_button.setEnabled(not value);self.download_button.setEnabled(not value and self.release is not None);self.cancel_button.setEnabled(value and self.release is not None)

    def start(self,task,callback):
        if self.task and self.task.isRunning():return
        if self.task:self.task.deleteLater()
        self.task=task;self.busy(True)
        task.done.connect(callback);task.failed.connect(self.failed);task.progress.connect(self.show_progress)
        task.finished.connect(lambda:self.busy(False));task.start()

    def check(self):
        self.release=None;self.download_button.setEnabled(False)
        self.state.setText('Consultando versões publicadas no GitHub…');self.start(UpdateTask(parent=self),self.checked)

    def checked(self,release):
        self.release=release
        if release is None:
            self.state.setText(f'Você está na versão {VERSION}. Nenhum hotfix mais recente com instalador verificável foi encontrado.');self.remote_notes.hide()
        else:
            kind=' · prévia para validação' if release.preview else ''
            self.state.setText(f'Nova versão: {release.version}{kind} · {release.size/1024/1024:.1f} MB. Revise as notas e escolha Baixar.')
            self.remote_notes.setPlainText(release.notes);self.remote_notes.show()
        self.busy(False)

    def download(self):
        if not self.release:return
        folder=QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
        path,_=QFileDialog.getSaveFileName(self,'Salvar instalador do hotfix',str(Path(folder)/self.release.filename),'Instalador Windows (*.exe)')
        if not path:return
        try:self.window.s.backup()
        except Exception as error:
            QMessageBox.warning(self,'Backup antes do hotfix',f'Não foi possível preservar o banco: {error}');return
        self.progress.setValue(0);self.progress.show();self.state.setText('Baixando o instalador. O aplicativo e o banco continuam em uso normal.')
        self.start(UpdateTask(self.release,path,self),self.downloaded)

    def show_progress(self,current,total):self.progress.setValue(int(current*100/max(1,total)))

    def downloaded(self,path):
        self.progress.setValue(100);self.state.setText(f'Instalador salvo e SHA-256 conferido: {path}\nFaça backup, feche o ERP e execute esse arquivo manualmente para instalar. Seus dados ficam preservados na pasta do ERP 2.0.')
        QMessageBox.information(self,'Hotfix baixado',f'Arquivo salvo em:\n{path}\n\nFaça backup e feche o aplicativo antes de executar o instalador. Ele não será aberto automaticamente.')

    def cancel(self):
        if self.task:self.task.cancel.set();self.state.setText('Cancelando o download…')

    def failed(self,message):self.state.setText(message);self.busy(False)

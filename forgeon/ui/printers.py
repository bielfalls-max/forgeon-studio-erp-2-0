from PySide6.QtWidgets import QDialog,QVBoxLayout,QFormLayout,QComboBox,QLineEdit,QLabel,QDialogButtonBox,QMessageBox
from ..business.printers import profiles,save_profile


class PrinterProfilesDialog(QDialog):
    def __init__(self,erp,parent=None):
        super().__init__(parent);self.erp=erp;self.setWindowTitle('Perfis de impressoras · referências editáveis');self.resize(640,330)
        layout=QVBoxLayout(self);form=QFormLayout();layout.addLayout(form)
        self.profile=QComboBox()
        for key,data in profiles(erp.s).items():self.profile.addItem(data['name'],key)
        self.power=QLineEdit();self.machine=QLineEdit()
        form.addRow('Impressora',self.profile);form.addRow('Consumo médio estimado (W)',self.power);form.addRow('Máquina: desgaste/manutenção R$/h',self.machine)
        note=QLabel('Referências de orçamento PLA: A1 120 W, AD5X 150 W e SPARKX i7 150 W. São hipóteses médias editáveis, não medições nem potência nominal. Máquina R$ 1/h é uma reserva provisória; ajuste pelo investimento, vida útil em horas e manutenção. 110/127 V não define sozinho o consumo. A tarifa em R$/kWh fica em Editar custos e taxas. Salvar modifica este perfil para novas estimativas dos produtos vinculados.');note.setWordWrap(True);layout.addWidget(note)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel);buttons.accepted.connect(self.save);buttons.rejected.connect(self.reject);layout.addWidget(buttons)
        self.profile.currentIndexChanged.connect(self.load);self.load()

    def load(self):
        data=profiles(self.erp.s)[self.profile.currentData()];self.power.setText(data['power_w']);self.machine.setText(data['machine_hour'])

    def save(self):
        try:
            save_profile(self.erp.s,self.profile.currentData(),self.power.text(),self.machine.text());self.accept()
        except Exception as error:QMessageBox.warning(self,'Verifique os valores',str(error))

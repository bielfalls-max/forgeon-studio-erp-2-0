# Avisos das bibliotecas incluídas

O aplicativo usa Qt/PySide6 e shiboken6 6.8.3, sob as licenças disponibilizadas pelo projeto Qt, incluindo LGPL versão 3. Os textos LGPL-3.0 e GPL-3.0 (referenciada pela LGPL) acompanham este pacote. Foram obtidos sem alteração de:

- https://github.com/qt/qtbase/blob/v6.8.3/LICENSES/LGPL-3.0-only.txt
- https://github.com/qt/qtbase/blob/v6.8.3/LICENSES/GPL-3.0-only.txt

Fontes correspondentes das bibliotecas Qt e bindings, sem modificações do Forgeon:

- https://github.com/qt/qtbase/tree/v6.8.3
- https://github.com/qt/pyside-setup/tree/v6.8.3
- https://download.qt.io/archive/qt/6.8/6.8.3/

As bibliotecas são distribuídas como DLLs separadas na pasta `_internal`, sem UPX e sem ligação estática. É permitido substituir as bibliotecas LGPL por versões modificadas compatíveis e realizar engenharia reversa para depurar tais modificações, conforme a licença aplicável. A redistribuição deve respeitar as condições das licenças originais. Esse aviso não altera a licença de nenhum componente.

As distribuições Python (PySide6, Essentials, Addons, shiboken6, openpyxl, et_xmlfile e defusedxml) mantêm seus metadados `.dist-info` no pacote, com autoria, termos e referência ao projeto de origem. A licença do Python do ambiente de compilação Windows é copiada para `licenses/Python`. Consulte também `docs/DEPENDENCIAS_E_SEGURANCA.md` e as distribuições oficiais de cada projeto para os termos completos. PyInstaller e Inno Setup são ferramentas de compilação; seu uso não atribui uma licença nova ao código do Forgeon.

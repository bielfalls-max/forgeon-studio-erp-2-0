"""Estimativas de orçamento PLA, não potência nominal ou medição da tomada."""
from .numbers import decimal
from .organization import preference,set_preference

PROFILES={
    'a1':{'name':'Bambu Lab A1 · 110/127 V','power_w':'120','machine_hour':'1.00'},
    'ad5x':{'name':'Flashforge AD5X · 110/127 V','power_w':'150','machine_hour':'1.00'},
    'sparkx_i7':{'name':'Creality SPARKX i7 · 110/127 V','power_w':'150','machine_hour':'1.00'},
}

def profiles(s):
    return {key:{**data,**preference(s,'printer:'+key,{})} for key,data in PROFILES.items()}

def detect_printer(name):
    name=name.casefold()
    if 'ad5x' in name:return 'ad5x'
    if 'sparkx' in name:return 'sparkx_i7'
    if 'a1' in name and 'mini' not in name:return 'a1'
    return 'custom'

def save_profile(s,key,power,machine):
    if key not in PROFILES:raise ValueError('Perfil de impressora inválido.')
    set_preference(s,'printer:'+key,{'power_w':str(decimal(power,'Consumo médio W')),'machine_hour':str(decimal(machine,'Máquina R$/h'))})

def initialize_costs(erp):
    s=erp.s
    if preference(s,'cost_defaults_hf12',False):return
    s.backup();settings=s.settings()
    with s.transaction():
        for key,value in {'packaging_default':'0.53','labor_unit':'2','loss_percent':'10'}.items():
            s.db.execute('INSERT OR IGNORE INTO settings VALUES(?,?)',(key,value))
        # Mantém referências já personalizadas. Somente os antigos padrões são trocados.
        for key,old,new in [('energy_kwh','1','1.10'),('power_w','150','140')]:
            if settings.get(key)==old:s.db.execute('UPDATE settings SET value=? WHERE key=?',(new,key))
        s.db.execute("UPDATE products SET packaging_cents=53 WHERE packaging_cents=0 AND NOT EXISTS(SELECT 1 FROM product_supplies WHERE product_id=products.id)")
        from .costs import stamp
        stamp(s,'cost:initial_hf12',{'source':'Estimativa de orçamento: energia SP 1,10/kWh; média das 3 máquinas 140 W; máquina 1,00/h; perdas 10%; mão de obra 2,00/un.; embalagem 0,53/un.'})
        s.db.execute("INSERT INTO preferences VALUES('cost_defaults_hf12','true')")
        s.log('referencias_iniciais_hf12',{'embalagem_cents':53,'mao_de_obra_cents':200,'perdas_percent':'10','preserva_custos_congelados':True})

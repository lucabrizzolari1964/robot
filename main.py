import machine
import time
from machine import Pin, I2C, PWM
import utime

ultima_lettura_a = 0
ultima_lettura_b = 0
DEBOUNCE_MS = 5 # Ignora segnali più veloci di 5ms

# --- CONFIGURAZIONE I2C E PCF8575 ---
i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=100000)
PCF_ADDR = 0x20

# --- CONFIGURAZIONE PWM (MOTORI) ---
pwm_a = PWM(Pin(25), freq=1000, duty=0)
pwm_b = PWM(Pin(27), freq=1000, duty=0)

# --- CONFIGURAZIONE ENCODER (INTERRUPT) ---
# Collega il cavetto del segnale (BIANCO) ai pin 34 e 35
enc_a_pin = Pin(26, Pin.IN, Pin.PULL_UP)
enc_b_pin = Pin(32, Pin.IN, Pin.PULL_UP)

passi_a = 0
passi_b = 0

# Funzioni di callback per il conteggio passi
def callback_enc_a(pin):
    global passi_a, ultima_lettura_a
    ora = utime.ticks_ms()
    # Se il tempo passato dall'ultimo impulso è > DEBOUNCE_MS
    if utime.ticks_diff(ora, ultima_lettura_a) > DEBOUNCE_MS:
        passi_a += 1
        ultima_lettura_a = ora

def callback_enc_b(pin):
    global passi_b, ultima_lettura_b
    ora = utime.ticks_ms()
    if utime.ticks_diff(ora, ultima_lettura_b) > DEBOUNCE_MS:
        passi_b += 1
        ultima_lettura_b = ora

# Attivazione degli Interrupt (reagiscono al passaggio di luce nel foto-accoppiatore)
enc_a_pin.irq(trigger=Pin.IRQ_FALLING, handler=callback_enc_a)
enc_b_pin.irq(trigger=Pin.IRQ_FALLING, handler=callback_enc_b)

def pcf_write(val_16bit):
    # Invia i 16 bit divisi in due byte (Low Byte e High Byte)
    buffer = bytearray([val_16bit & 0xFF, (val_16bit >> 8) & 0xFF])
    i2c.writeto(PCF_ADDR, buffer)

def controllo_motori(dir_a, dir_b, velocita=900):
    """
    dir: 0=fermo, 1=avanti, 2=indietro
    Mappatura accertata: 
    Motore A: P9 e P10
    Motore B: P8 e P11
    """
    valore = 0xFFFF # Logica Inversa: 1 = OFF/Freno
    
    # Motore A
    if dir_a == 1:       # Avanti
        valore &= ~(1 << 9)
    elif dir_a == 2:     # Indietro
        valore &= ~(1 << 10)
        
    # Motore B
    if dir_b == 1:       # Avanti
        valore &= ~(1 << 8)
    elif dir_b == 2:     # Indietro
        valore &= ~(1 << 11)

    # Applica i segnali di direzione
    pcf_write(valore)
    
    # Imposta la velocità
    duty_a = velocita if dir_a != 0 else 0
    duty_b = velocita if dir_b != 0 else 0
    pwm_a.duty(duty_a)
    pwm_b.duty(duty_b)

def reset_passi():
    global passi_a, passi_b
    passi_a = 0
    passi_b = 0

# --- ESEMPIO DI TEST CON ENCODER ---

try:
    print("Test Encoder: Muovo avanti per 5000 passi")
    reset_passi()
    controllo_motori(1, 1, 800) # Avanti a velocità 800
    
    # Continua finché uno dei due motori non raggiunge 500 passi
    while passi_a < 5000 and passi_b < 5000:
        print("Passi A:", passi_a, "| Passi B:", passi_b, end="\r")
        time.sleep_ms(10)
    
    print("Target raggiunto. Fermo tutto.")
    controllo_motori(0, 0)
    time.sleep(2)
    
    print("Test Rotazione: Indietro per 5000 passi")
    reset_passi()
    controllo_motori(2, 2, 800)
    while passi_a < 5000 and passi_b < 5000:
        print("Passi A:", passi_a, "| Passi B:", passi_b, end="\r")
        time.sleep_ms(10)
    time.sleep(2)
    controllo_motori(0, 0)

except KeyboardInterrupt:
    # Sicurezza: ferma i motori se premi Ctrl+C
    controllo_motori(0, 0)
    print("Programma interrotto")

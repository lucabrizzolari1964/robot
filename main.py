import machine
import time
import micropython
import sys

# Emergenza RAM per gestire errori negli interrupt
micropython.alloc_emergency_exception_buf(100)

# --- CONFIGURAZIONE PIN ---
# Encoder: Pin 14 (A) e 33 (B) con resistenze di pull-up
encoder_A = machine.Pin(14, machine.Pin.IN, machine.Pin.PULL_UP)
encoder_B = machine.Pin(33, machine.Pin.IN, machine.Pin.PULL_UP)

# Driver Motore (Esempio per L298N o TB6612)
pwm_a = machine.PWM(machine.Pin(13), freq=1000, duty=0)
ain1 = machine.Pin(4, machine.Pin.OUT, value=0)
ain2 = machine.Pin(17, machine.Pin.OUT, value=0)

pwm_b = machine.PWM(machine.Pin(27), freq=1000, duty=0)
bin1 = machine.Pin(26, machine.Pin.OUT, value=0)
bin2 = machine.Pin(25, machine.Pin.OUT, value=0)

# --- STATO E FILTRI ---
target_A = 0
target_B = 0
last_time_A = 0
last_time_B = 0
FILTRO_US = 1500  # Aumentato a 1.5ms per filtrare disturbi elettrici dei motori

# --- INTERRUPT (Ottimizzati) ---
@micropython.native
def cb_a(pin):
    global target_A, last_time_A
    t = time.ticks_us()
    if time.ticks_diff(t, last_time_A) > FILTRO_US:
        if target_A > 0:
            target_A -= 1
        last_time_A = t

@micropython.native
def cb_b(pin):
    global target_B, last_time_B
    t = time.ticks_us()
    if time.ticks_diff(t, last_time_B) > FILTRO_US:
        if target_B > 0:
            target_B -= 1
        last_time_B = t

encoder_A.irq(trigger=machine.Pin.IRQ_FALLING, handler=cb_a)
encoder_B.irq(trigger=machine.Pin.IRQ_FALLING, handler=cb_b)

# --- FUNZIONE MOVIMENTO ---
def muovi_motori(pA, pB, vel_max):
    global target_A, target_B
    target_A = abs(pA)
    target_B = abs(pB)
    
    # --- GESTIONE DIREZIONE MOTORE A ---
    if pA >= 0:
        ain1.value(1); ain2.value(0) # Avanti
    else:
        ain1.value(0); ain2.value(1) # Indietro
        
    # --- GESTIONE DIREZIONE MOTORE B ---
    if pB >= 0:
        bin1.value(1); bin2.value(0) # Avanti
    else:
        bin1.value(0); bin2.value(1) # Indietro
    
    print("\n[VAI] Target A:{} B:{} Vel:{}".format(pA, pB, vel_max))
    
    while True:
        irq_state = machine.disable_irq()
        tA = target_A
        tB = target_B
        machine.enable_irq(irq_state)
        
        if tA <= 0 and tB <= 0:
            break 
            
        if tA > 0:
            pwr_a = min(vel_max, max(350, tA * 12)) 
            pwm_a.duty(pwr_a)
        else:
            pwm_a.duty(0)
            # Spegniamo i pin di direzione per questo motore
            ain1.value(0); ain2.value(0) 

        if tB > 0:
            pwr_b = min(vel_max, max(350, tB * 12))
            pwm_b.duty(pwr_b)
        else:
            pwm_b.duty(0)
            bin1.value(0); bin2.value(0) 
            
        print("Mancano -> A:{} | B:{}    ".format(tA, tB), end="\r")
        time.sleep_ms(5)
    
    # Assicura spegnimento totale e freno
    pwm_a.duty(0); pwm_b.duty(0)
    ain1.value(1); ain2.value(1) # Esempio Freno Attivo
    bin1.value(1); bin2.value(1)
    time.sleep_ms(100)
    ain1.value(0); ain2.value(0); bin1.value(0); bin2.value(0) # Rilascio
    print("\n[STOP] Destinazione raggiunta.")

# --- LETTURA SERIALE ---
def leggi_seriale():
    buffer = ""
    print("\nInserisci: PassiA,PassiB,Vel (es. 500,500,600)")
    print(">> ", end="")
    while True:
        if sys.stdin.any(): # Se c'è qualcosa nel buffer seriale
            char = sys.stdin.read(1)
            if char in ('\r', '\n'):
                if len(buffer) > 0:
                    return buffer
            else:
                buffer += char
                print(char, end="")
        time.sleep_ms(10)

# --- LOOP PRINCIPALE ---
print("\n--- ROBOT PRONTO ---")
while True:
    try:
        # Per test automatico usa il comando sotto, altrimenti usa leggi_seriale()
        comando = "1150,1150,600" 
        print("\nMotore A e B avanti ... inizio ciclo di test")
        # comando = leggi_seriale()
        
        parti = [int(x.strip()) for x in comando.split(',')]
        if len(parti) == 3:
            muovi_motori(parti[0], parti[1], parti[2])
            
        print("\nAttesa 3 secondi...")
        time.sleep(3)
        comando = "1150,-1150,800" 
        print("\nMotore A avanti e motore B indietro ...")
        # comando = leggi_seriale()
        
        parti = [int(x.strip()) for x in comando.split(',')]
        if len(parti) == 3:
            muovi_motori(parti[0], parti[1], parti[2])
            
        print("\nAttesa 3 secondi...")
        time.sleep(3)
        comando = "-1150,1150,800" 
        print("\nMotore A indietro e motore B avanti ...")
        # comando = leggi_seriale()
        
        parti = [int(x.strip()) for x in comando.split(',')]
        if len(parti) == 3:
            muovi_motori(parti[0], parti[1], parti[2])
            
        print("\nAttesa 3 secondi...")
        time.sleep(3)
        comando = "-1150,-1150,800" 
        print("\nMotore A indietro e motore B indietro ...")
        # comando = leggi_seriale()
        
        parti = [int(x.strip()) for x in comando.split(',')]
        if len(parti) == 3:
            muovi_motori(parti[0], parti[1], parti[2])
            
        print("\nAttesa 3 secondi...")
        time.sleep(3)
        
    except KeyboardInterrupt:
        print("\nProgramma interrotto.")
        pwm_a.duty(0); pwm_b.duty(0)
        break
    except Exception as e:
        print("\nErrore:", e)
        target_A = 0; target_B = 0
        pwm_a.duty(0); pwm_b.duty(0)
        time.sleep(2)

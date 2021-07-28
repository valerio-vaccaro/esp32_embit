from m5 import display
from fonts import (
    vga1_8x8,
    vga2_8x8,
    vga1_8x16,
    vga2_8x16,
    vga1_16x16,
    vga2_16x16,
    vga1_bold_16x16,
    vga2_bold_16x16,
    vga1_bold_16x32,
    vga2_bold_16x32,
    )
from st7789py import (
    BLACK,
    BLUE,
    RED,
    GREEN,
    CYAN,
    MAGENTA,
    YELLOW,
    WHITE,
    )
from bitcoin import (
    bip32,
    bip39,
    script,
    hashes,
    psbt,
)
from bitcoin.networks import NETWORKS
from binascii import (
    unhexlify,
    hexlify,
    a2b_base64,
    b2a_base64,
    )
from machine import Pin
import sys
import uselect
import json

VERSION = "0.0.1"
BACKGROUND = BLACK
FOREGROUND = GREEN

WALLET = {
    'name': 'default',
    'network': 'testnet',
    'mnemonic': 'alien visual jealous source coral memory embark certain radar capable clip edit',
    'path': 'm/84h/1h/0h',
    }

LED = Pin(10, Pin.OUT)
BUTTON_A = False
BUTTON_B = False
HSM_MODE = False
JSON_MODE = False


def button_a(irq):
    global BUTTON_A
    BUTTON_A = not BUTTON_A


def button_b(irq):
    global BUTTON_B
    BUTTON_B = not BUTTON_B


def splashscreen(title, subtitle):
    display.fill(BACKGROUND)
    display.rotation(1)
    display.text(vga1_bold_16x32, title, 5, 5, FOREGROUND, BACKGROUND)
    display.text(vga1_8x8, subtitle, 5, 40, FOREGROUND, BACKGROUND)
    display.text(font_little, "version "+VERSION, 5, 120, FOREGROUND, BACKGROUND)


def confirmscreen(title, subtitle, hsm=False):
    global BUTTON_A
    global BUTTON_B
    BUTTON_A = False
    display.fill(BACKGROUND)
    display.rotation(1)
    display.text(vga1_bold_16x32, title, 5, 5, FOREGROUND, BACKGROUND)
    display.text(vga1_8x8, subtitle, 5, 40, FOREGROUND, BACKGROUND)
    prev_button_a = not BUTTON_A
    prev_button_b = BUTTON_B
    while prev_button_b == BUTTON_B:
        if prev_button_a != BUTTON_A:
            display.fill_rect(0, 110, 240, 25, BACKGROUND)
            if not BUTTON_A:
                display.rect(5, 110, 110, 20, GREEN)
                display.text(vga1_8x16, "YES", 45, 112, WHITE, BACKGROUND)
                display.fill_rect(125, 110, 110, 20, RED)
                display.text(vga1_8x16, "NO", 170, 112, WHITE, RED)
            else:
                display.fill_rect(5, 110, 110, 20, GREEN)
                display.text(vga1_8x16, "YES", 45, 112, BACKGROUND, GREEN)
                display.rect(125, 110, 110, 20, RED)
                display.text(vga1_8x16, "NO", 170, 112, WHITE, BACKGROUND)
            prev_button_a = BUTTON_A
            if hsm:
                BUTTON_A = True
                prev_button_b = not prev_button_b
    prev_button_b = BUTTON_B
    return BUTTON_A

def messagescreen(title, subtitle, message):
    display.fill(BACKGROUND)
    display.rotation(1)
    display.text(vga1_bold_16x32, title, 5, 5, FOREGROUND, BACKGROUND)
    display.text(vga1_8x8, subtitle, 5, 40, FOREGROUND, BACKGROUND)
    chars_per_line = 27
    for i in range(1, 8):
        display.text(vga1_8x8, message[(i-1)*chars_per_line:i*chars_per_line+1], 10, 60+i*10, YELLOW, BACKGROUND)

def pubkeyscreen():
    messagescreen("Bitcoin", "Extended pubkey", "")
    LED.value(False)
    seed = bip39.mnemonic_to_seed(WALLET['mnemonic'])
    if WALLET['network'] == 'mainnet':
        root = bip32.HDKey.from_seed(seed, version=NETWORKS['main']['xprv'])
    elif WALLET['network'] == 'testnet':
        root = bip32.HDKey.from_seed(seed, version=NETWORKS['test']['xprv'])
    else:
        root = None
    fingerprint = root.child(0).fingerprint
    xprv = root.derive(WALLET['path'])
    xpub = xprv.to_public()
    buf = '[' + hexlify(fingerprint).decode("utf-8") + WALLET['path'][1:] + ']' + xpub.to_base58()
    messagescreen("Bitcoin", "Extended pubkey", buf)
    LED.value(True)
    print('\n\033[32m'+buf+'\033[0m')


def addressscreen(path):
    messagescreen("Bitcoin", "Address", "")
    LED.value(False)
    seed = bip39.mnemonic_to_seed(WALLET['mnemonic'])
    if WALLET['network'] == 'mainnet':
        root = bip32.HDKey.from_seed(seed, version=NETWORKS['main']['xprv'])
    elif WALLET['network'] == 'testnet':
        root = bip32.HDKey.from_seed(seed, version=NETWORKS['test']['xprv'])
    else:
        root = None
    fingerprint = root.child(0).fingerprint
    xprv = root.derive(WALLET['path'])
    priv = xprv.derive(path)
    sc = script.p2wpkh(priv)
    if WALLET['network'] == 'mainnet':
        buf = sc.address(NETWORKS["main"])
    elif WALLET['network'] == 'testnet':
        buf = sc.address(NETWORKS["test"])
    else:
        buf = ''
    print('\n\033[32m'+buf+'\033[0m')
    messagescreen("Bitcoin", "Address", buf)
    LED.value(True)

def signmessage(path, message):
    LED.value(False)
    seed = bip39.mnemonic_to_seed(WALLET['mnemonic'])
    if WALLET['network'] == 'mainnet':
        root = bip32.HDKey.from_seed(seed, version=NETWORKS['main']['xprv'])
    elif WALLET['network'] == 'testnet':
        root = bip32.HDKey.from_seed(seed, version=NETWORKS['test']['xprv'])
    else:
        root = None
    fingerprint = root.child(0).fingerprint
    xprv = root.derive(WALLET['path'])
    priv = xprv.derive(path)
    sc = script.p2wpkh(priv)
    if WALLET['network'] == 'mainnet':
        buf = sc.address(NETWORKS["main"])
    elif WALLET['network'] == 'testnet':
        buf = sc.address(NETWORKS["test"])
    else:
        buf = ''
    hash = hashes.sha256(message)
    signature = priv.sign(hash)
    LED.value(True)
    return signature

def decodepsbt(psbtstr):
    seed = bip39.mnemonic_to_seed(WALLET['mnemonic'])
    if WALLET['network'] == 'mainnet':
        root = bip32.HDKey.from_seed(seed, version=NETWORKS['main']['xprv'])
    elif WALLET['network'] == 'testnet':
        root = bip32.HDKey.from_seed(seed, version=NETWORKS['test']['xprv'])
    else:
        root = None
    fingerprint = root.child(0).fingerprint
    
    tx = psbt.PSBT.parse(a2b_base64(psbtstr))
    # print how much we are spending and where
    total_in = 0

    for inp in tx.inputs:
        total_in += inp.witness_utxo.value
    print("Inputs:", total_in, "satoshi")

    change_out = 0 # value that goes back to us
    send_outputs = []
    for i, out in enumerate(tx.outputs):
        # check if it is a change or not:
        change = False
        # should be one or zero for single-key addresses
        for pub in out.bip32_derivations:
            # check if it is our key
            if out.bip32_derivations[pub].fingerprint == fingerprint:
                hdkey = root.derive(out.bip32_derivations[pub].derivation)
                mypub = hdkey.key.get_public_key()
                if mypub != pub:
                    raise ValueError("Derivation path doesn't look right")
                # now check if provided scriptpubkey matches
                sc = script.p2wpkh(mypub)
                if sc == tx.tx.vout[i].script_pubkey:
                    change = True
                    continue
        if change:
            change_out += tx.tx.vout[i].value
        else:
            send_outputs.append(tx.tx.vout[i])

    print("Spending", total_in-change_out, "satoshi")
    fee = total_in-change_out
    for out in send_outputs:
        fee -= out.value
        print(out.value,"to",out.script_pubkey.address(NETWORKS["test"]))
    print("Fee:",fee,"satoshi")

def signpsbt(psbtstr):
    LED.value(False)
    seed = bip39.mnemonic_to_seed(WALLET['mnemonic'])
    if WALLET['network'] == 'mainnet':
        root = bip32.HDKey.from_seed(seed, version=NETWORKS['main']['xprv'])
    elif WALLET['network'] == 'testnet':
        root = bip32.HDKey.from_seed(seed, version=NETWORKS['test']['xprv'])
    else:
        root = None
    fingerprint = root.child(0).fingerprint
    xprv = root.derive(WALLET['path'])
    psbtstruct = psbt.PSBT.parse(a2b_base64(psbtstr))
    psbtstruct.sign_with(xprv)
    LED.value(True)
    return psbtstr

def help():
    print('\n \
- HELP -\n \
\n \
\033[36mHelp\033[0m\n \
h - this help\n \
\n \
\033[36mMnemonic management\033[0m\n \
ms:mnemonic - mnemonic set\n \
mg - mnemonic get\n \
\n \
\033[36mPath management\033[0m\n \
ps:path - path set\n \
pg - path get\n \
\n \
\033[36mExtended pubkey\033[0m\n \
xg - extended pubkey get\n \
\n \
\033[36mAddress\033[0m\n \
ag:derivation - address get derivation\n \
\n \
\033[36mSign\033[0m\n \
sm:derivation:message - sign message\n \
sp:psbt - sign psbt\n \
\n \
\033[36mHSM mode\033[0m\n \
H - toggle HSM mode\n \
')


# Function to read a character from USB serial or return None.
def kbhit():
    spoll=uselect.poll()        # Set up an input polling object.
    spoll.register(sys.stdin,uselect.POLLIN)    # Register polling object.
    kbch = sys.stdin.read(1) if spoll.poll(0) else None
    spoll.unregister(sys.stdin)
    return(kbch)


def getcommand():
    buf = ''
    print('$ ', end='')
    while True:
        new_ch = kbhit()
        if new_ch == None:
            continue
        elif new_ch == '\n':
            break
        else:
            print(new_ch, end='', sep='')
            buf = buf + new_ch
    return buf


def executecommand(fullcommand):
    global HSM_MODE
    global WALLET
    global BACKGROUND
    if len(fullcommand) > 0:
        command = fullcommand[0]
    else:
        command = ' '

    if command == 'h': # help
        help()

    if command == 'H': # HSM
        if confirmscreen('HSM', 'Toggle HSM mode?'):
            HSM_MODE = not HSM_MODE
        if HSM_MODE:
            print('\n\033[32m HSM active\033[0m')
            BACKGROUND = BLUE
        else:
            print('\n\033[32m HSM not active\033[0m')
            BACKGROUND = BLACK

    elif command == 'm': # mnemonic
        if len(fullcommand) > 1:
            subcommand = fullcommand[1]
        else:
            subcommand = ' '
        if subcommand == 's': #
            if confirmscreen('Bitcoin', 'Update mnemonic?'):
                print('set mnemonic to '+fullcommand[3:])
            else:
                print('\n')

        elif subcommand == 'g': # get
            if confirmscreen('Bitcoin', 'Show mnemonic?'):
                print('\n\033[32m'+mnemonic+'\033[0m')
            else:
                print('\n')
        else:
             print('\n\033[31mUnknown subcommand\033[0m')

    elif command == 'p': # path
        if len(fullcommand) > 1:
            subcommand = fullcommand[1]
        else:
            subcommand = ' '
        if subcommand == 's': # set
            print('\n')
        elif subcommand == 'g': # get
            if confirmscreen('Bitcoin', 'Show path?'):
                print('\n\033[32m'+path+'\033[0m')
            else:
                print()
        else:
             print('\n\033[31mUnknown subcommand\033[0m')

    elif command == 'x': # extended pubkey
        if confirmscreen('Bitcoin', 'Show extended pubkey?'):
            pubkeyscreen()

    elif command == 'a': # address
        if len(fullcommand) > 1:
            subcommand = fullcommand[1]
        else:
            subcommand = ' '
        if subcommand == 'g': # get
            if confirmscreen('Bitcoin', 'Show address?'):
                addressscreen('m/0/0')
            else:
                print('\n')

    elif command == 's': # sign
        if len(fullcommand) > 1:
            subcommand = fullcommand[1]
        else:
            subcommand = ' '
        if subcommand == 'm': # message
            if confirmscreen('Bitcoin', 'Sign message?', HSM_MODE):
                signature = signmessage('m/0/0', 'pippo')
                der = signature.serialize()
                print('\n\033[32m',der,'\033[0m','\n')
            else:
                print('\n')
        elif subcommand == 'p': # psbt
            psbt = "cHNidP8BAHICAAAAAY3LB6teEH6qJHluFYG3AQe8n0HDUcUSEuw2WIJ1ECDUAAAAAAD/////AoDDyQEAAAAAF6kU882+nVMDKGj4rKzjDB6NjyJqSBCHaPMhCgAAAAAWABQUbW8/trQg4d3PKL8WLi2kUa1BqAAAAAAAAQEfAMLrCwAAAAAWABTR6Cr4flM2A0LMGjGiaZ+fhod37SIGAhHf737H1jCUjkJ1K5DqFkaY0keihxeWBQpm1kDtVZyxGLMX7IZUAACAAQAAgAAAAIAAAAAAAAAAAAAAIgIDPtTTi27VFw59jdmWDV8b1YciQzhYGO7m8zB9CvD0brcYsxfshlQAAIABAACAAAAAgAEAAAAAAAAAAA=="
            decodepsbt(psbt)
            if confirmscreen('Bitcoin', 'Sign PSBT?', HSM_MODE):
                signedpsbt = signpsbt(psbt)
                print('\n\033[32m',signedpsbt,'\033[0m','\n')
            else:
                print('\n')
        else:
             print('\n\033[31mUnknown subcommand\033[0m')

    else:
        print('\n\033[31mUnknown command\033[0m')


def main():
    LED.value(True)
    BUTTON_A_dev = Pin(39, Pin.IN, Pin.PULL_UP)
    BUTTON_B_dev = Pin(37, Pin.IN, Pin.PULL_UP)
    BUTTON_A_dev.irq(trigger = Pin.IRQ_FALLING, handler = button_a)
    BUTTON_B_dev.irq(trigger = Pin.IRQ_FALLING, handler = button_b)

    try:
        f = open('default.wal', 'r')
        print('\nOpen default wallet\n')
        #WALLET = json.loads()
        f.close()
    except OSError:
        f = open('default.wal', 'w')
        print('\nCreate default wallet\n')
        f.write(json.dumps(WALLET))
        f.close()

    repeat = True
    help()
    while repeat:
        splashscreen('Bitcoin', 'Python HWW')

        command = getcommand()
        executecommand(command)

    sys.stdin.close()
    print(sys.version)
    sys.exit(0)


if __name__ == "__main__":
    main()

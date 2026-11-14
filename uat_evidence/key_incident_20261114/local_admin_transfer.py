"""PROPOSED administrator-local helper. Requires PI local-display/clipboard exception.
Never run in an AI/cloud/shared/recorded browser environment. No network or install.
Decrypts the existing encrypted bundle only in memory. Displays key NAMES only.
Official provider settings may display pasted values to the administrator.
"""
import base64
import json
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from generate_encrypted_bundle import AAD, material


def unlock(path, password):
    raw = Path(path).read_bytes()
    if len(raw) > 16000:
        raise ValueError('BUNDLE_REJECTED')
    b = json.loads(raw)
    if set(b) != {'format', 'kdf', 'salt', 'nonce', 'ciphertext'} or b['format'] != AAD.decode() or b['kdf'] != 'scrypt-n32768-r8-p1':
        raise ValueError('BUNDLE_REJECTED')
    salt = base64.b64decode(b['salt'], validate=True)
    nonce = base64.b64decode(b['nonce'], validate=True)
    if len(salt) != 16 or len(nonce) != 12:
        raise ValueError('BUNDLE_REJECTED')
    key = Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(password.encode())
    m = json.loads(AESGCM(key).decrypt(nonce, base64.b64decode(b['ciphertext'], validate=True), AAD))
    root = base64.b64decode(m['gas']['ADMIN_BRIDGE_SIGNING_KEY'], validate=True)
    if m != material(root):
        raise ValueError('BUNDLE_TARGET_OR_DERIVATION_MISMATCH')
    return m


def main():
    import tkinter as tk
    from tkinter import filedialog, simpledialog, messagebox
    app = tk.Tk()
    app.title('JUOG isolated rotation — LOCAL ADMIN ONLY')
    app.geometry('650x360')
    tk.Label(app, text='Do NOT use with AI access, screen recording/sharing, clipboard history or sync.\nRequires PI exception for local administrator display/paste.\nThis helper does not change GAS or Streamlit settings.', wraplength=620).pack(pady=10)
    if not messagebox.askyesno('Local-only confirmation', 'PI local-display/paste exception approved?\nClipboard history/sync and recording/sharing disabled?\nTrusted local administrator workstation?'):
        app.destroy(); return
    path = filedialog.askopenfilename(title='Select encrypted rotation bundle', filetypes=[('JSON', '*.json')])
    if not path:
        app.destroy(); return
    password = simpledialog.askstring('Unlock locally', 'Bundle passphrase (never send to AI):', show='*')
    if password is None:
        app.destroy(); return
    try:
        m = unlock(path, password)
    except Exception:
        messagebox.showerror('Stopped', 'BUNDLE_REJECTED. No installation attempted.')
        app.destroy(); return
    password = None
    status = tk.StringVar(value='No value displayed. Select one exact destination below.')
    tk.Label(app, textvariable=status, wraplength=620).pack(pady=8)
    held = [None]
    timer = [None]
    def clear():
        if held[0] is not None:
            try:
                if app.clipboard_get() == held[0]:
                    app.clipboard_clear(); app.update_idletasks()
            except tk.TclError:
                pass
        held[0] = None
        status.set('Clipboard cleared if still owned by this helper. History/sync cannot be cleared here.')
    def copy_value(label, value):
        if timer[0] is not None: app.after_cancel(timer[0])
        app.clipboard_clear(); app.clipboard_append(value); app.update_idletasks()
        held[0] = value
        status.set(label + ': copied locally for 45 seconds; paste only to the named isolated setting.')
        timer[0] = app.after(45000, clear)
    fields = [(f'GAS / {k}', v) for k, v in m['gas'].items()]
    fields += [('Streamlit / juog_identity_bridge.signing_key', m['streamlit']['juog_identity_bridge.signing_key'])]
    for label, value in fields:
        tk.Button(app, text=label, command=lambda l=label, v=value: copy_value(l, v)).pack(fill='x', padx=12, pady=2)
    def close():
        clear(); m.clear(); fields.clear(); app.destroy()
    tk.Button(app, text='Clear clipboard and close', command=close).pack(pady=10)
    app.protocol('WM_DELETE_WINDOW', close)
    app.mainloop()

if __name__ == '__main__':
    try:
        main()
    except Exception:
        # Never print an exception, decrypted object, key or response.
        raise SystemExit('LOCAL_TRANSFER_STOPPED; no automatic installation attempted') from None

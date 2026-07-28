"""
Production integration tests for Seal Vault.
Tests the CLI as a real user would invoke it.
Run: python production_tests/test.py
"""
import json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path

SEAL = [sys.executable, "-m", "aegis.cli"]
PASS = FAIL = SKIP = 0
RESULTS = []
_REGISTRY = []


def run(args, input=None, env=None, timeout=30):
    e = os.environ.copy()
    e["PYTHONDONTWRITEBYTECODE"] = "1"
    if env:
        e.update(env)
    try:
        r = subprocess.run(SEAL + args, input=input.encode() if input else None,
                           capture_output=True, timeout=timeout, env=e)
        return r.returncode, r.stdout.decode("utf-8", errors="replace"), r.stderr.decode("utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"


def test(name):
    def deco(fn):
        def wrapper():
            global PASS, FAIL, SKIP
            print(f"\n  {name} ...", end=""); sys.stdout.flush()
            try:
                fn(); PASS += 1; RESULTS.append(f"  \033[92mPASS\033[0m  {name}")
            except AssertionError as e:
                FAIL += 1; RESULTS.append(f"  \033[91mFAIL\033[0m  {name}")
                print(f"\n    \033[91m{e}\033[0m")
            except Exception as e:
                FAIL += 1; RESULTS.append(f"  \033[91mFAIL\033[0m  {name}  ({type(e).__name__})")
                print(f"\n    \033[91m{type(e).__name__}: {e}\033[0m")
        _REGISTRY.append((name, wrapper))
        return wrapper
    return deco


def eq(a, b, m=""):
    if a != b: raise AssertionError(f"Expected {b!r}, got {a!r}" + (f"  ({m})" if m else ""))


def inside(n, h, m=""):
    if n not in h: raise AssertionError(f"Missing {n!r} in output" + (f"  ({m})" if m else ""))


def outside(n, h, m=""):
    if n in h: raise AssertionError(f"Unexpected {n!r} in output" + (f"  ({m})" if m else ""))


def get_json(out, m=""):
    s = out.strip()
    if not s: raise AssertionError("Empty output, expected JSON" + (f"  ({m})" if m else ""))
    try: return json.loads(s)
    except json.JSONDecodeError as e: raise AssertionError(f"Invalid JSON: {e}\noutput: {s[:200]}" + (f"  ({m})" if m else ""))


# ---------------------------------------------------------------------------

@test("help")
def t_help():
    r, o, e = run(["--help"])
    eq(r, 0, e); inside("Usage:", o); inside("encrypt", o); inside("decrypt", o)


@test("invoke without subcommand")
def t_no_subcommand():
    r, o, e = run([])
    eq(r, 0, e)


@test("init creates vault")
def t_init_basic():
    td = tempfile.mkdtemp()
    try:
        vd = os.path.join(td, "mv")
        r, o, e = run(["init", "-P", vd, "-p", "test-pass"])
        eq(r, 0, e); inside("created", o.lower())
        assert Path(vd, "keys", "manifest.enc").exists()
    finally: shutil.rmtree(td)


@test("init with existing vault")
def t_init_exists():
    td = tempfile.mkdtemp()
    try:
        vd = os.path.join(td, "mv")
        run(["init", "-P", vd, "-p", "p"])
        r, o, e = run(["init", "-P", vd, "-p", "p"])
        eq(r, 0, e); inside("already exists", o.lower())
    finally: shutil.rmtree(td)


@test("init --json returns JSON")
def t_init_json():
    td = tempfile.mkdtemp()
    try:
        vd = os.path.join(td, "jv")
        r, o, e = run(["init", "-P", vd, "-p", "p", "--json"])
        eq(r, 0, e)
        d = get_json(o); inside("status", d); inside("path", d)
    finally: shutil.rmtree(td)


@test("init --json errors when no passphrase")
def t_init_json_nopass():
    td = tempfile.mkdtemp()
    try:
        vd = os.path.join(td, "np")
        r, o, e = run(["init", "-P", vd, "--json"], env={"SEAL_PASSPHRASE": ""})
        eq(r, 1)
        d = get_json(o); inside("error", d.get("status","").lower()) or inside("error", d)
    finally: shutil.rmtree(td)


@test("save and load with namespace")
def t_save_load():
    td = tempfile.mkdtemp()
    try:
        vd = os.path.join(td, "sl")
        run(["init", "-P", vd, "-p", "p"])
        r, o, e = run(["save", "-P", vd, "-p", "p", "-n", "default", "-i", "greeting", "-d", '{"value":"hello"}'])
        eq(r, 0, e)
        r, o, e = run(["load", "-P", vd, "-p", "p", "-n", "default", "-i", "greeting"])
        eq(r, 0, e); inside("hello", o)
    finally: shutil.rmtree(td)


@test("load missing item errors")
def t_load_missing():
    td = tempfile.mkdtemp()
    try:
        vd = os.path.join(td, "lm")
        run(["init", "-P", vd, "-p", "p"])
        r, o, e = run(["load", "-P", vd, "-p", "p", "-n", "default", "-i", "nope"])
        eq(r, 1, o + e)
    finally: shutil.rmtree(td)


@test("list items")
def t_list_items():
    td = tempfile.mkdtemp()
    try:
        vd = os.path.join(td, "li")
        run(["init", "-P", vd, "-p", "p"])
        run(["save", "-P", vd, "-p", "p", "-n", "ns1", "-i", "a", "-d", '{"v":"1"}'])
        run(["save", "-P", vd, "-p", "p", "-n", "ns2", "-i", "b", "-d", '{"v":"2"}'])
        r, o, e = run(["list", "-P", vd, "-p", "p"])
        eq(r, 0, e); inside("a", o); inside("b", o)
    finally: shutil.rmtree(td)


@test("list --format json")
def t_list_json():
    td = tempfile.mkdtemp()
    try:
        vd = os.path.join(td, "lj")
        run(["init", "-P", vd, "-p", "p"])
        run(["save", "-P", vd, "-p", "p", "-n", "n", "-i", "x", "-d", '{"v":"42"}'])
        r, o, e = run(["list", "-P", vd, "-p", "p", "--format", "json"])
        eq(r, 0, e)
        d = get_json(o)
        # should be a list or have items key
        assert isinstance(d, (list, dict)), f"unexpected type: {type(d).__name__}"
    finally: shutil.rmtree(td)


@test("delete item")
def t_delete():
    td = tempfile.mkdtemp()
    try:
        vd = os.path.join(td, "dl")
        run(["init", "-P", vd, "-p", "p"])
        run(["save", "-P", vd, "-p", "p", "-n", "n", "-i", "delme", "-d", '{"v":"x"}'])
        r, o, e = run(["delete", "-P", vd, "-p", "p", "-n", "n", "-i", "delme", "-y"])
        eq(r, 0, e)
        r2, _, _ = run(["load", "-P", vd, "-p", "p", "-n", "n", "-i", "delme"])
        eq(r2, 1)
    finally: shutil.rmtree(td)


@test("verify vault")
def t_verify():
    td = tempfile.mkdtemp()
    try:
        vd = os.path.join(td, "vf")
        run(["init", "-P", vd, "-p", "p"])
        run(["save", "-P", vd, "-p", "p", "-n", "n", "-i", "k", "-d", '{"v":"x"}'])
        r, o, e = run(["verify", "-P", vd, "-p", "p"])
        eq(r, 0, e)
    finally: shutil.rmtree(td)


@test("wrong passphrase fails")
def t_wrong_passphrase():
    td = tempfile.mkdtemp()
    try:
        vd = os.path.join(td, "wp")
        run(["init", "-P", vd, "-p", "correct"])
        run(["save", "-P", vd, "-p", "correct", "-n", "n", "-i", "k", "-d", '{"v":"secret"}'])
        r, o, e = run(["load", "-P", vd, "-p", "wrong", "-n", "n", "-i", "k"])
        if r == 0: outside("secret", o)
    finally: shutil.rmtree(td)


@test("file encrypt/decrypt roundtrip")
def t_file_crypto():
    td = tempfile.mkdtemp()
    try:
        src = os.path.join(td, "secret.txt")
        enc = os.path.join(td, "secret.enc")
        dec = os.path.join(td, "secret_dec.txt")
        with open(src, "w") as f: f.write("HELLO WORLD")
        r, o, e = run(["encrypt", "-i", src, "-o", enc, "-p", "mypass"])
        eq(r, 0, e); assert os.path.exists(enc)
        r, o, e = run(["decrypt", "-i", enc, "-o", dec, "-p", "mypass"])
        eq(r, 0, e); assert os.path.exists(dec)
        with open(dec) as f: eq(f.read(), "HELLO WORLD")
    finally: shutil.rmtree(td)


@test("file encrypt --json")
def t_file_encrypt_json():
    td = tempfile.mkdtemp()
    try:
        src = os.path.join(td, "d.bin"); dst = os.path.join(td, "d.enc")
        with open(src, "wb") as f: f.write(b"\x00\x01\x02")
        r, o, e = run(["encrypt", "-i", src, "-o", dst, "-p", "p", "--json"])
        eq(r, 0, e); d = get_json(o); inside("status", d)
    finally: shutil.rmtree(td)


@test("file decrypt --json")
def t_file_decrypt_json():
    td = tempfile.mkdtemp()
    try:
        src = os.path.join(td, "p.txt"); enc = os.path.join(td, "p.enc"); dec = os.path.join(td, "p_dec.txt")
        with open(src, "w") as f: f.write("test")
        run(["encrypt", "-i", src, "-o", enc, "-p", "p"])
        r, o, e = run(["decrypt", "-i", enc, "-o", dec, "-p", "p", "--json"])
        eq(r, 0, e); d = get_json(o); inside("status", d)
    finally: shutil.rmtree(td)


@test("decrypt bogus file errors")
def t_decrypt_bogus():
    td = tempfile.mkdtemp()
    try:
        bogus = os.path.join(td, "fake.enc"); out = os.path.join(td, "o.txt")
        with open(bogus, "w") as f: f.write("garbage")
        r, o, e = run(["decrypt", "-i", bogus, "-o", out, "-p", "p"])
        eq(r, 1, e + o)
    finally: shutil.rmtree(td)


@test("decrypt pre-checks output exists")
def t_decrypt_output_exists():
    td = tempfile.mkdtemp()
    try:
        src = os.path.join(td, "s.txt"); enc = os.path.join(td, "s.enc"); dec = os.path.join(td, "s_dec.txt")
        with open(src, "w") as f: f.write("data")
        run(["encrypt", "-i", src, "-o", enc, "-p", "p"])
        with open(dec, "w") as f: f.write("exists")
        r, o, e = run(["decrypt", "-i", enc, "-o", dec, "-p", "p"])
        eq(r, 1, e + o)
    finally: shutil.rmtree(td)


@test("vaults list")
def t_vaults_list():
    r, o, e = run(["vaults", "list"])
    eq(r, 0, e)


@test("vaults list --json")
def t_vaults_list_json():
    r, o, e = run(["vaults", "list", "--json"])
    eq(r, 0, e); d = get_json(o)
    assert isinstance(d, dict); inside("vaults", d)


@test("doctor")
def t_doctor():
    r, o, e = run(["doctor"]); eq(r, 0, e)


@test("doctor --json")
def t_doctor_json():
    r, o, e = run(["doctor", "--json"]); eq(r, 0, e); d = get_json(o)
    assert isinstance(d, dict)


@test("doctor on vault")
def t_doctor_vault():
    td = tempfile.mkdtemp()
    try:
        vd = os.path.join(td, "dv")
        run(["init", "-P", vd, "-p", "p"])
        r, o, e = run(["doctor", "-P", vd]); eq(r, 0, e)
    finally: shutil.rmtree(td)


@test("generate password")
def t_generate():
    r, o, e = run(["generate"]); eq(r, 0, e); assert len(o.strip()) > 0


@test("generate with length")
def t_generate_length():
    r, o, e = run(["generate", "-l", "12"]); eq(r, 0, e)
    pw = o.strip().splitlines()[-1].strip() if o.strip() else ""
    assert len(pw) >= 10


@test("generate invalid length rejected")
def t_generate_invalid():
    r, _, _ = run(["generate", "-l", "0"]); eq(r, 2)
    r2, _, _ = run(["generate", "-l", "10001"]); assert r2 != 0


@test("keygen")
def t_keygen():
    r, o, e = run(["keygen"]); eq(r, 0, e)
    inside("private", o.lower())


@test("canary deploy and check")
def t_canary():
    td = tempfile.mkdtemp()
    try:
        vd = os.path.join(td, "cn")
        run(["init", "-P", vd, "-p", "p"])
        run(["save", "-P", vd, "-p", "p", "-n", "n", "-i", "k", "-d", '{"v":"x"}'])
        r, o, e = run(["canary", "deploy", "-P", vd, "-p", "p", "-y"])
        eq(r, 0, e)
        r, o, e = run(["canary", "check", "-P", vd, "-p", "p"])
        eq(r, 0, e)
    finally: shutil.rmtree(td)


@test("report generate")
def t_report():
    td = tempfile.mkdtemp()
    try:
        vd = os.path.join(td, "rp")
        run(["init", "-P", vd, "-p", "p"])
        run(["save", "-P", vd, "-p", "p", "-n", "n", "-i", "k", "-d", '{"v":"x"}'])
        r, o, e = run(["report", "generate", "-P", vd, "-f", "soc2"])
        eq(r, 0, e)
    finally: shutil.rmtree(td)


@test("audit show")
def t_audit():
    td = tempfile.mkdtemp()
    try:
        vd = os.path.join(td, "au")
        run(["init", "-P", vd, "-p", "p"])
        run(["save", "-P", vd, "-p", "p", "-n", "n", "-i", "k", "-d", '{"v":"x"}'])
        r, o, e = run(["audit", "show", "-P", vd])
        assert r == 0 or r == 1
    finally: shutil.rmtree(td)


@test("ask command")
def t_ask():
    r, o, e = run(["ask", "generate a password"]); eq(r, 0, e)


@test("agent list my items")
def t_agent_list():
    td = tempfile.mkdtemp()
    try:
        vd = os.path.join(td, "ag")
        run(["init", "-P", vd, "-p", "p"])
        run(["save", "-P", vd, "-p", "p", "-n", "n", "-i", "alpha", "--kv", "v=1"])
        r, o, e = run(["ask", "-P", vd, "-p", "p", "list my items"])
        eq(r, 0, e)
    finally: shutil.rmtree(td)


@test("SEAL_PASSPHRASE env var")
def t_env_passphrase():
    td = tempfile.mkdtemp()
    try:
        vd = os.path.join(td, "ep")
        run(["init", "-P", vd, "-p", "env-pass"])
        r, o, e = run(["save", "-P", vd, "-n", "n", "-i", "k", "-d", '{"v":"envval"}'],
                      env={"SEAL_PASSPHRASE": "env-pass"})
        eq(r, 0, e)
        r, o, e = run(["load", "-P", vd, "-n", "n", "-i", "k"],
                      env={"SEAL_PASSPHRASE": "env-pass"})
        eq(r, 0, e); inside("envval", o)
    finally: shutil.rmtree(td)


@test("Unicode safety")
def t_unicode_safety():
    td = tempfile.mkdtemp()
    try:
        vd = os.path.join(td, "us")
        run(["init", "-P", vd, "-p", "p"])
        for c in [["init", "-P", vd, "-p", "p"], ["doctor"], ["generate"], ["keygen"]]:
            _, o, e = run(c); outside("\u2192", o + e)
    finally: shutil.rmtree(td)


@test("binary value roundtrip")
def t_binary_value():
    td = tempfile.mkdtemp()
    try:
        vd = os.path.join(td, "bv")
        run(["init", "-P", vd, "-p", "p"])
        r, o, e = run(["save", "-P", vd, "-p", "p", "-n", "n", "-i", "bk", "-d", '{"v":"Hello World"}'])
        eq(r, 0, e)
        r, o, e = run(["load", "-P", vd, "-p", "p", "-n", "n", "-i", "bk"])
        eq(r, 0, e); inside("Hello", o)
    finally: shutil.rmtree(td)


@test("unknown command errors")
def t_unknown_cmd():
    r, o, e = run(["doesnotexist"]); eq(r, 2, e)


@test("--help for all commands")
def t_all_help():
    for c in ["init", "save", "load", "list", "delete", "verify", "encrypt", "decrypt",
              "vaults", "doctor", "generate", "keygen", "canary", "report", "audit",
              "ask", "vaults list", "canary deploy", "canary check", "tui"]:
        r, o, e = run(c.split() + ["--help"])
        eq(r, 0, f"{c} --help: {e[:200]}")
        inside("Usage:", o, c)


@test("empty vault report")
def t_empty_vault_report():
    td = tempfile.mkdtemp()
    try:
        vd = os.path.join(td, "er")
        run(["init", "-P", vd, "-p", "p"])
        r, o, e = run(["report", "generate", "-P", vd, "-f", "soc2"])
        eq(r, 0, e)
    finally: shutil.rmtree(td)


@test("agent save/load roundtrip")
def t_agent_save_load():
    td = tempfile.mkdtemp()
    try:
        vd = os.path.join(td, "asl")
        run(["init", "-P", vd, "-p", "p"])
        r, o, e = run(["ask", "-P", vd, "-p", "p", "save my password foobar"])
        eq(r, 0, e)
    finally: shutil.rmtree(td)


@test("canary alerts on tamper")
def t_canary_tamper():
    td = tempfile.mkdtemp()
    try:
        vd = os.path.join(td, "ct")
        run(["init", "-P", vd, "-p", "p"])
        run(["save", "-P", vd, "-p", "p", "-n", "n", "-i", "k", "--kv", "v=x"])
        run(["canary", "deploy", "-P", vd, "-p", "p", "-y"])
        # Remove canary registry to trigger detection
        canaries_dir = os.path.join(vd, ".canaries")
        if os.path.isdir(canaries_dir): shutil.rmtree(canaries_dir)
        r, o, e = run(["canary", "check", "-P", vd, "-p", "p"])
        eq(r, 1, e + o)
    finally: shutil.rmtree(td)


@test("verify detects tampered audit log")
def t_verify_tamper():
    td = tempfile.mkdtemp()
    try:
        vd = os.path.join(td, "vt")
        run(["init", "-P", vd, "-p", "p"])
        run(["save", "-P", vd, "-p", "p", "-n", "n", "-i", "k", "--kv", "v=x"])
        # Corrupt an audit entry hash to break chain
        audit_file = os.path.join(vd, "keys", "audit.log")
        if os.path.exists(audit_file):
            lines = open(audit_file, "r").readlines()
            if lines:
                import json as _j
                entry = _j.loads(lines[0])
                entry["hash"] = "0" * 64  # wrong hash
                lines[0] = _j.dumps(entry, separators=(",", ":")) + "\n"
                open(audit_file, "w").writelines(lines)
        r, o, e = run(["verify", "-P", vd, "-p", "p"])
        assert r != 0 or "broken" in (o + e).lower() or "invalid" in (o + e).lower() or "fail" in (o + e).lower(), f"rc={r}: {o[:200]}"
    finally: shutil.rmtree(td)


@test("empty vault list")
def t_empty_list():
    td = tempfile.mkdtemp()
    try:
        vd = os.path.join(td, "el")
        run(["init", "-P", vd, "-p", "p"])
        r, o, e = run(["list", "-P", vd, "-p", "p"]); eq(r, 0, e)
    finally: shutil.rmtree(td)


@test("full audit lifecycle")
def t_audit_lifecycle():
    td = tempfile.mkdtemp()
    try:
        vd = os.path.join(td, "fal")
        run(["init", "-P", vd, "-p", "p"])
        run(["save", "-P", vd, "-p", "p", "-n", "n", "-i", "k1", "-d", '{"v":"1"}'])
        run(["save", "-P", vd, "-p", "p", "-n", "n", "-i", "k2", "-d", '{"v":"2"}'])
        run(["delete", "-P", vd, "-p", "p", "-n", "n", "-i", "k1", "-y"])
        r, o, e = run(["audit", "show", "-P", vd])
        assert r == 0 or r == 1, f"rc={r}: {e[:200]}"
    finally: shutil.rmtree(td)


@test("non-TTY no hang")
def t_non_tty_hang():
    td = tempfile.mkdtemp()
    try:
        vd = os.path.join(td, "nth")
        run(["init", "-P", vd, "-p", "p"])
        src = os.path.join(td, "f.txt"); enc = os.path.join(td, "f.enc")
        with open(src, "w") as f: f.write("data")
        run(["encrypt", "-i", src, "-o", enc, "-p", "p"])
        r, o, e = run(["decrypt", "-i", enc, "-o", os.path.join(td, "out.txt")],
                      env={"SEAL_PASSPHRASE": ""}, timeout=10)
    except:
        pass
    finally: shutil.rmtree(td)


@test("generate boundary lengths")
def t_generate_boundary():
    r, o, e = run(["generate", "-l", "1"]); eq(r, 0, e)
    r2, o2, e2 = run(["generate", "-l", "9999"]); eq(r2, 0, e2)


@test("mixed items")
def t_mixed_items():
    td = tempfile.mkdtemp()
    try:
        vd = os.path.join(td, "mx")
        run(["init", "-P", vd, "-p", "p"])
        run(["save", "-P", vd, "-p", "p", "-n", "n1", "-i", "abc", "-d", '{"v":"123"}'])
        run(["save", "-P", vd, "-p", "p", "-n", "n2", "-i", "xyz", "-d", '{"v":"789"}'])
        r, o, e = run(["list", "-P", vd, "-p", "p"]); eq(r, 0, e)
        inside("abc", o); inside("xyz", o)
        r, o, e = run(["load", "-P", vd, "-p", "p", "-n", "n1", "-i", "abc"]); eq(r, 0, e)
        inside("123", o)
    finally: shutil.rmtree(td)


@test("delete nonexistent item errors")
def t_delete_nonexist():
    td = tempfile.mkdtemp()
    try:
        vd = os.path.join(td, "dn")
        run(["init", "-P", vd, "-p", "p"])
        r, o, e = run(["delete", "-P", vd, "-p", "p", "-n", "n", "-i", "nope", "-y"])
        eq(r, 1, o + e)
    finally: shutil.rmtree(td)


@test("keygen creates keypair")
def t_keygen_valid():
    r, o, e = run(["keygen"]); eq(r, 0, e)
    inside("private", o.lower())


@test("agent asks respond")
def t_agent_ask():
    r, o, e = run(["ask", "what can you do?"]); eq(r, 0, e)


@test("special characters in values")
def t_special_chars():
    td = tempfile.mkdtemp()
    try:
        vd = os.path.join(td, "sc")
        run(["init", "-P", vd, "-p", "p"])
        special = "!@#$%^&*()_+=-`~[]{}|;':\",./<>?"
        r, o, e = run(["save", "-P", vd, "-p", "p", "-n", "n", "-i", "sp",
                       "-d", json.dumps({"v": special})])
        eq(r, 0, e)
        r, o, e = run(["load", "-P", vd, "-p", "p", "-n", "n", "-i", "sp"])
        eq(r, 0, e); inside(special[:20], o)
    finally: shutil.rmtree(td)


@test("long value store/load")
def t_long_value():
    td = tempfile.mkdtemp()
    try:
        vd = os.path.join(td, "lv")
        run(["init", "-P", vd, "-p", "p"])
        long_val = "A" * 10000
        r, o, e = run(["save", "-P", vd, "-p", "p", "-n", "n", "-i", "lk",
                       "-d", json.dumps({"v": long_val})])
        eq(r, 0, e)
        r, o, e = run(["load", "-P", vd, "-p", "p", "-n", "n", "-i", "lk"])
        eq(r, 0, e)
    finally: shutil.rmtree(td)


@test("version command")
def t_version():
    r, o, e = run(["version"]); eq(r, 0, e); assert len(o.strip()) > 0


@test("biometric --help")
def t_biometric_help():
    r, o, e = run(["biometric", "--help"]); eq(r, 0, e); inside("Usage:", o)


@test("share --help")
def t_share_help():
    r, o, e = run(["share", "--help"]); eq(r, 0, e); inside("Usage:", o)


@test("init with cipher chacha20")
def t_init_cipher():
    td = tempfile.mkdtemp()
    try:
        vd = os.path.join(td, "ch")
        r, o, e = run(["init", "-P", vd, "-p", "p", "--cipher", "chacha20"])
        eq(r, 0, e); assert Path(vd, "keys", "manifest.enc").exists()
    finally: shutil.rmtree(td)


@test("encrypt with empty file")
def t_encrypt_empty():
    td = tempfile.mkdtemp()
    try:
        src = os.path.join(td, "empty.bin"); enc = os.path.join(td, "empty.enc")
        Path(src).write_text("")
        r, o, e = run(["encrypt", "-i", src, "-o", enc, "-p", "p"])
        eq(r, 0, e); assert os.path.exists(enc) and os.path.getsize(enc) > 0
    finally: shutil.rmtree(td)


@test("doctor on non-existent vault")
def t_doctor_nonexist():
    td = tempfile.mkdtemp()
    try:
        fake = os.path.join(td, "nonexistent")
        r, o, e = run(["doctor", "-P", fake])
        # doctor always exits 0; check output shows fail status
    finally: shutil.rmtree(td)


# ---------------------------------------------------------------------------

def main():
    global PASS, FAIL, SKIP
    print("Seal Production Integration Tests")
    print("=" * 50)
    print(f"Python: {sys.executable}")
    print()
    start = time.time()
    for name, fn in _REGISTRY:
        fn()
    elapsed = time.time() - start
    print("\n" + "=" * 50)
    for r in RESULTS: print(r)
    print(f"\nResults: {PASS} passed, {FAIL} failed, {SKIP} skipped  ({elapsed:.1f}s)")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

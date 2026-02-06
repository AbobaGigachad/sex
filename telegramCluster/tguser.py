#!/usr/bin/env python3
"""
Конфигуратор Telegram-инстансов для Docker Swarm.
Создаёт сервисы (tg-PHONE) на worker-нодах, подключает к стеку tgstack (mongo, redis).
Данные: /mnt/telegram/users/<phone>/
"""
import os
import shutil
import subprocess
import sys
from time import sleep

STACK_NAME = "tgstack"
NETWORK = f"{STACK_NAME}_device_environment"
TG_DIR = "/mnt/telegram/users"
TG_IMAGE = "chat2desktech/tg_docker:TG-135"
PORT_FILE = ".port"
# Replica set: primary + secondary; read запросы на secondary (readPreference=secondaryPreferred)
MONGO_URL = (
    f"mongodb://{STACK_NAME}_mongo_primary:27017,{STACK_NAME}_mongo_secondary:27017/"
    "?replicaSet=rs0&readPreference=secondaryPreferred"
)
MONGO_REPLICA_SET = "rs0"
REDIS_URL = f"redis://{STACK_NAME}_redis:6379"


def main_menu():
    while True:
        cmd = input(
            "Welcome to Telegram configurator (Swarm).\n"
            "1 - create new instance\n"
            "2 - start tg instance\n"
            "3 - start or stop all clickers\n"
            "4 - list all instances\n"
            "5 - connect to tg console (logs)\n"
            "6 - stop tg instance\n"
            "7 - stop and delete tg instance\n"
            "8 - restart tg instance\n"
            "9 - toggle auto-read\n"
            "10 - toggle message loader\n"
            "11 - toggle qr-authorisation\n"
        ).strip()

        if cmd == "1":
            create()
        elif cmd == "2":
            start(manual=True)
        elif cmd == "3":
            print("1 - start all\n2 - stop all\n3 - restart all")
            s = input().strip()
            if s == "1":
                start_all()
            elif s == "2":
                stop_all()
            elif s == "3":
                restart_all()
        elif cmd == "4":
            tg_list()
        elif cmd == "5":
            console_connect()
        elif cmd == "6":
            stop()
        elif cmd == "7":
            delete()
        elif cmd == "8":
            phone = input("Enter client's phone: ").strip()
            restart_clicker(phone)
        elif cmd == "9":
            toggle_autoread()
        elif cmd == "10":
            toggle_message_loader()
        elif cmd == "11":
            toggle_auth_method()


def create():
    phone = input("Enter client's phone: ").strip()
    while not phone.isdigit() or len(phone) < 5:
        phone = input('The number can only contain numbers. Try again or type "exit" for back to main menu.\n').strip()
        if phone == "exit":
            return
    if is_exist(phone):
        print("Phone number already exist")
        return

    server_list = {
        "ru": "https://gw.chat2desk.com",
        "eu": "https://gw.chat24.io",
        "kz": "https://gw.chat2desk.kz",
        "mx": "https://gw.chat2desk.com.mx",
        "forex": "https://gw-c2d.forextime.com",
        "renins": "https://gw-renins.chat2desk.com",
        "mediasol": "https://gw-salescs.chat2desk.com",
        "gw20": "https://gw-test20.chat2desk.com",
        "duxgr": "https://gw-duxgroup.omniomni.io",
        "mfua": "https://gw-mfua.chat2desk.com",
        "alabuga": "https://gw-alabuga.chat2desk.com",
        "sreda": "https://gw-c2d.sreda.ru",
        "sw": "https://gw-simple.chat2desk.com",
        "custom": "Enter manually",
    }
    print("Select server:")
    for key in server_list:
        print(f"  {key} - {server_list[key]}")
    key = input("\n").strip()
    while key not in server_list:
        key = input('Wrong server. Try again or type "exit" for back to main menu.\n').strip()
        if key == "exit":
            return
    server = input("Enter gateway URL: ").strip() if key == "custom" else server_list[key]

    port = get_port()
    os.makedirs(TG_DIR, exist_ok=True)
    user_dir = os.path.join(TG_DIR, phone)
    os.mkdir(user_dir)
    cfg_dir = os.path.join(user_dir, "tg_configs")
    os.makedirs(os.path.join(cfg_dir, "logfiles"), exist_ok=True)
    downloads_dir = os.path.join(user_dir, "telegram_downloads")
    os.makedirs(os.path.join(downloads_dir, "media"), exist_ok=True)
    os.makedirs(os.path.join(downloads_dir, "users"), exist_ok=True)

    env_content = f"""telegram.app_data.phone_number={phone}
gateway.url={server}
application_api_port=5001
mongo_db.url={MONGO_URL}
mongo_db.replica_set={MONGO_REPLICA_SET}
debug=false
logger_level=INFO
telegram.session.folder_path=/telegram/config/
MIGRATION_LIST=tg_135
telegram.last_message_loader.dialogs_limit=100
telegram.last_message_loader.last_message_timestamp=259200
telegram.last_message_loader.messages_limit=100
telegram.messages.read_acknowledge_after_recieve=true
redis.url={REDIS_URL}
"""
    env_path = os.path.join(user_dir, ".env")
    with open(env_path, "w") as env:
        env.write(env_content)

    with open(os.path.join(user_dir, PORT_FILE), "w") as f:
        f.write(port)

    service_name = f"tg-{phone}"
    print([phone, server, port, f"service={service_name}"])
    if input("Start? y/n: ").strip().lower() == "y":
        start(phone, manual=True)


def start(phone=None, manual=False):
    if phone is None:
        phone = input("Enter client's phone: ").strip()
    if is_running(phone):
        print(f"{phone} - Clicker already running")
        return
    if not is_exist(phone):
        print(f"{phone} - Clicker not found")
        return

    service_name = f"tg-{phone}"
    user_dir = os.path.join(TG_DIR, phone)
    cfg_dir = os.path.join(user_dir, "tg_configs")
    env_path = os.path.join(user_dir, ".env")

    cmd = [
        "docker", "service", "create",
        "--name", service_name,
        "--network", NETWORK,
        "--env-file", env_path,
        f"--mount", f"type=bind,source={TG_DIR},target=/telegram/static",
        "--mount", f"type=bind,source={cfg_dir},target=/telegram/config",
        "--constraint", "node.role==worker",
        "--replicas", "1",
        "--label", "tg_clicker=1",
        TG_IMAGE,
    ]
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode != 0:
        print(f"Error: {out.stderr or out.stdout}")
        return
    print(f"{phone} started (service {service_name})")
    if manual and input("Show logs? y/n: ").strip().lower() == "y":
        console_connect(phone)


def stop(phone=None):
    if phone is None:
        phone = input("Enter client's phone: ").strip()
    if not is_exist(phone):
        print(f"{phone} - Clicker not found")
        return
    service_name = f"tg-{phone}"
    if not is_running(phone):
        print(f"{phone} - Clicker not running")
        return
    subprocess.run(["docker", "service", "rm", service_name], check=True, capture_output=True)
    print(f"{phone} stopped")


def restart_clicker(phone):
    print(f"Restarting {phone}...")
    stop(phone)
    sleep(2)
    start(phone, manual=True)


def start_all():
    for name in os.listdir(TG_DIR):
        path = os.path.join(TG_DIR, name)
        if os.path.isdir(path) and os.path.isfile(os.path.join(path, ".env")):
            start(name)


def stop_all():
    out = subprocess.run(
        ["docker", "service", "ls", "--filter", "label=tg_clicker=1", "--format", "{{.Name}}"],
        capture_output=True, text=True
    )
    for line in out.stdout.strip().splitlines():
        line = line.strip()
        if line.startswith("tg-"):
            phone = line[3:]
            stop(phone)


def restart_all():
    out = subprocess.run(
        ["docker", "service", "ls", "--filter", "label=tg_clicker=1", "--format", "{{.Name}}"],
        capture_output=True, text=True
    )
    for line in out.stdout.strip().splitlines():
        line = line.strip()
        if line.startswith("tg-"):
            stop(line[3:])
    sleep(5)
    for name in os.listdir(TG_DIR):
        path = os.path.join(TG_DIR, name)
        if os.path.isdir(path) and os.path.isfile(os.path.join(path, ".env")):
            start(name)
            sleep(2)


def tg_list():
    subprocess.run(["docker", "service", "ls", "--filter", "label=tg_clicker=1"])


def console_connect(phone=None):
    if phone is None:
        phone = input("Enter client's phone: ").strip()
    if not is_exist(phone):
        print(f"{phone} - Clicker not found")
        return
    service_name = f"tg-{phone}"
    if is_running(phone):
        print(f"Logs for {service_name} (Ctrl+C to exit):")
        subprocess.run(["docker", "service", "logs", "-f", service_name])
    else:
        print(f"{phone} - Clicker not running")


def delete():
    phone = input("Enter client's phone: ").strip()
    if input("Are you sure? (Yes/No): ").strip() != "Yes":
        return
    stop(phone)
    user_dir = os.path.join(TG_DIR, phone)
    if os.path.isdir(user_dir):
        shutil.rmtree(user_dir, ignore_errors=True)
    print(f"{phone} - Deleted")


def get_port():
    port_list = []
    for name in os.listdir(TG_DIR):
        path = os.path.join(TG_DIR, name)
        if os.path.isdir(path):
            pfile = os.path.join(path, PORT_FILE)
            if os.path.isfile(pfile):
                try:
                    with open(pfile) as f:
                        port_list.append(f.read().strip())
                except (OSError, ValueError):
                    pass
    for port in range(7001, 8000):
        if str(port) not in port_list:
            return str(port)
    raise Exception("No free ports left")


def is_exist(phone):
    return os.path.isdir(os.path.join(TG_DIR, phone))


def is_running(phone):
    service_name = f"tg-{phone}"
    out = subprocess.run(
        ["docker", "service", "ls", "--filter", f"name={service_name}", "--format", "{{.Name}}"],
        capture_output=True, text=True
    )
    return service_name in (out.stdout or "")


def toggle_auth_method():
    phone = input("Enter client's phone: ").strip()
    env_file = os.path.join(TG_DIR, phone, ".env")
    if not os.path.isfile(env_file):
        print(f"{phone} - not found")
        return
    with open(env_file, "r") as f:
        lines = f.readlines()
    current = "false"
    for line in lines:
        if line.startswith("telegram.qr_authorisation"):
            current = line.strip().split("=")[1].lower()
            break
    print(f"Current qr-code-auth: {current.upper()}")
    choice = input("Set (true/false): ").strip().lower()
    if choice not in ("true", "false"):
        print("Invalid choice")
        return
    new_lines = []
    found = False
    for line in lines:
        if line.startswith("telegram.qr_authorisation"):
            new_lines.append(f"telegram.qr_authorisation={choice}\n")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"telegram.qr_authorisation={choice}\n")
    with open(env_file, "w") as f:
        f.writelines(new_lines)
    print(f"Qr-code-auth set to {choice.upper()}")
    restart_clicker(phone)


def toggle_autoread():
    phone = input("Enter client's phone: ").strip()
    env_file = os.path.join(TG_DIR, phone, ".env")
    if not os.path.isfile(env_file):
        print(f"{phone} - not found")
        return
    with open(env_file, "r") as f:
        lines = f.readlines()
    current = "true"
    for line in lines:
        if line.startswith("telegram.messages.read_acknowledge_after_recieve"):
            current = line.strip().split("=")[1].lower()
            break
    print(f"Current auto-read: {current.upper()}")
    choice = input("Set (true/false): ").strip().lower()
    if choice not in ("true", "false"):
        print("Invalid choice")
        return
    new_lines = []
    found = False
    for line in lines:
        if line.startswith("telegram.messages.read_acknowledge_after_recieve"):
            new_lines.append(f"telegram.messages.read_acknowledge_after_recieve={choice}\n")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"telegram.messages.read_acknowledge_after_recieve={choice}\n")
    with open(env_file, "w") as f:
        f.writelines(new_lines)
    print(f"Auto-read set to {choice.upper()}")
    restart_clicker(phone)


def toggle_message_loader():
    phone = input("Enter client's phone: ").strip()
    env_file = os.path.join(TG_DIR, phone, ".env")
    if not os.path.isfile(env_file):
        print(f"{phone} - not found")
        return
    default_on = {"dialogs_limit": 100, "last_message_timestamp": 259200, "messages_limit": 100}
    default_off = {"dialogs_limit": 1, "last_message_timestamp": 1, "messages_limit": 1}
    with open(env_file, "r") as f:
        lines = f.readlines()
    current_state = "ON"
    for line in lines:
        if line.startswith("telegram.last_message_loader.dialogs_limit"):
            current_state = "ON" if int(line.strip().split("=")[1]) > 1 else "OFF"
            break
    print(f"Current message loader: {current_state}")
    choice = input("Set (ON/OFF): ").strip().upper()
    if choice not in ("ON", "OFF"):
        print("Invalid choice")
        return
    loader_values = default_on if choice == "ON" else default_off
    keys = list(loader_values.keys())
    exists_keys = {k: False for k in keys}
    new_lines = []
    for line in lines:
        updated = False
        for k in keys:
            if line.startswith(f"telegram.last_message_loader.{k}"):
                new_lines.append(f"telegram.last_message_loader.{k}={loader_values[k]}\n")
                exists_keys[k] = True
                updated = True
                break
        if not updated:
            new_lines.append(line)
    for k in keys:
        if not exists_keys[k]:
            new_lines.append(f"telegram.last_message_loader.{k}={loader_values[k]}\n")
    with open(env_file, "w") as f:
        f.writelines(new_lines)
    print(f"Message loader set to {choice}")
    restart_clicker(phone)


def ensure_mnt_dirs():
    """Базовые каталоги в /mnt: users и logs (как на старом сервере)."""
    base = os.path.dirname(TG_DIR)
    for path in (TG_DIR, os.path.join(base, "logs")):
        try:
            os.makedirs(path, exist_ok=True)
        except OSError:
            pass


if __name__ == "__main__":
    ensure_mnt_dirs()
    if not os.path.isdir(TG_DIR):
        print(f"TG_DIR {TG_DIR} not found. Create it first.")
        sys.exit(1)
    main_menu()

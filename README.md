# Скрипты настройки Docker Swarm кластера

## Файлы

- **phienix.sh** - Скрипт автоматической раскатки Master ноды
- **setup_worker.sh** - Скрипт настройки Worker ноды

## Использование

### Master нода

Запустите на master ноде:

```bash
cd /home/chat2desk/tgcloud
./phienix.sh
```

Скрипт выполнит:
- Обновление системы
- Установку Docker, Docker Compose, fail2ban, python3
- Создание пользователя `security`
- Создание директории `tgcloud`
- Настройку NFS (если `/mnt` существует)
- Инициализацию Docker Swarm (если не инициализирован)

### Worker ноды

На каждой worker ноде выполните:

```bash
# 1. Скопируйте скрипт setup_worker.sh на worker ноду
# 2. Получите Worker Token с master ноды:
#    sudo docker swarm join-token worker -q

# 3. Запустите скрипт:
./setup_worker.sh <WORKER_TOKEN> <MASTER_IP>
```

Пример:
```bash
./setup_worker.sh SWMTKN-1-xxx 10.128.0.23
```

Скрипт выполнит:
- Обновление системы
- Установку Docker, Docker Compose, fail2ban, python3, nfs-common
- Подключение к Docker Swarm
- Настройку NFS mount (`/mnt`)

## Важно

После установки Docker на worker нодах:
- Перелогиньтесь или выполните `newgrp docker` для применения группы docker
- Проверьте подключение: `sudo docker node ls` (на master ноде)

## Текущие настройки

- **Master IP**: 10.128.0.23
- **Worker Token**: `SWMTKN-1-3w6gp81bymq6e7d0eh5vmmqnp9oxqpqqkrgthoj6jjcatdy4lf-do5qrynz0g4nsve13n3oqa2jw`
- **Worker ноды**: 51.250.4.176, 84.201.159.19, 89.169.136.241
- **NFS**: `/mnt` на master ноде, монтируется на всех worker нодах

## Быстрый старт для Worker нод

```bash
./setup_worker.sh SWMTKN-1-3w6gp81bymq6e7d0eh5vmmqnp9oxqpqqkrgthoj6jjcatdy4lf-do5qrynz0g4nsve13n3oqa2jw 10.128.0.23
```
# sex

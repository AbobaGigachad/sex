# tgstack

Стек: MongoDB 8.2.3 (replica set), Redis, Nginx. В Swarm — всё на master; приложения (tguser) на workers.

## Деплой

**Один хост:**

```bash
docker compose up -d
```

**Swarm:**

```bash
docker stack deploy -c docker-compose.yml tgstack
```

Первый раз создать каталоги (если нужно):

```bash
mkdir -p /mnt/telegram/users /mnt/tguser/tg_clickers
```

Инициализация replica set MongoDB (один раз после первого запуска):

```bash
# Compose:
docker exec mongo_primary mongosh --eval 'rs.initiate({_id:"rs0",members:[{_id:0,host:"mongo_primary:27017"},{_id:1,host:"mongo_secondary:27017"}]})'

# Swarm (имя стека tgstack):
cid=$(docker ps -q -f name=tgstack_mongo_primary | head -1)
docker exec $cid mongosh --eval 'rs.initiate({_id:"rs0",members:[{_id:0,host:"tgstack_mongo_primary:27017"},{_id:1,host:"tgstack_mongo_secondary:27017"}]})'
```

## Конфигуратор номеров

`telegramCluster/tguser.py` — создание/старт/стоп инстансов как сервисов Swarm на worker-нодах. Данные: `/mnt/telegram/users/<phone>/`.

Запуск (с master): `python3 telegramCluster/tguser.py`

## Домен и HTTPS

Nginx настроен на **tgcloud.chat2desk.com**. Для HTTPS положите сертификаты в `certs/`: `fullchain.pem`, `privkey.pem`. Затем перезапустите nginx.

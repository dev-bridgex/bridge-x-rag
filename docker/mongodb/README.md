# MongoDB with Docker Compose Setup

A step-by-step guide to running MongoDB using Docker Compose .

## Prerequisites
1. Docker installed (`sudo apt install docker.io`)
2. Docker Compose installed (`sudo apt install docker-compose`)
3. Basic terminal knowledge

## Setup Instructions

### 1. Create docker-compose file like the following:

```yaml
version: '3.7'
services:
  mongodb:
    image: bitnami/mongodb:8.0
    container_name: mongodb
    ports:
      - "27017:27017"
    volumes:
      - ./mongodb/initdb.d/init-mongo.js:/docker-entrypoint-initdb.d/mongo-init.js:ro
      - mongodb-data:/bitnami/mongodb
      - mongodb-log:/pot/bitnami/mongodb/logs
    networks:
      - bridgex-rag
    env_file:
      - ./.env
    environment:
      - MONGODB_ROOT_USER=${MONGODB_ROOT_USER}
      - MONGODB_ROOT_PASSWORD=${MONGODB_ROOT_PASSWORD}
      - MONGODB_USERNAME=${MONGODB_USERNAME}
      - MONGODB_PASSWORD=${MONGODB_PASSWORD}
      - MONGODB_DATABASE=${MONGODB_DATABASE}
      - MONGODB_EXTRA_FLAGS=--wiredTigerCacheSizeGB=2


    ## These Following Command Override Dosn't Work With Bitnami Images
    # command:
    #   - --storageEngine
    #   - wiredTiger
    #   - --auth
    #   - '--logpath'
    #   - '/var/log/mongodb/mongod.log'

    restart: always
  
networks:
  bridgex-rag:

volumes:
  mongodb-data:
    driver: local
  mongodb-log:
    driver: local

```

### 2. Create an init-mongo.js with the following content :


``` javascript
// Switch to admin database and authenticate
db = db.getSiblingDB("admin");
db.auth('admin', 'admin'); // Requires admin user with proper privileges [[9]]

// Switch to target database
db = db.getSiblingDB('your database name');

// Create user with proper syntax (role as string)
db.createUser({
    user: "your yousername",
    pwd: "your password",
    roles: [
      'readWrite' // Role format simplified [[1]][[3]][[7]]
    ]
});

// Create collection (requires valid user permissions)
db.createCollection('test_docker');
```

### 3. Run docker-compose to start running the container:

``` bash
docker-compose down && docker-compose build --no-cache && docker-compose up -d
```

### 4. To check everything is working, SSH into the MongoDB container like the following:

``` bash
# to SSH into the container
docker exec -it mongodb_contaner bash

mongod --version

# Check admin db connection is working or not
mongosh admin -u root -p

# check default database with newly created by init-mongo.js
show dbs
``` 


### 5. Take a backup from server and apply the dump in your local docker container:

cp the dump file inside the container:

``` bash 
docker cp /home/shaikh/projects/vadio_dump/staging/staging_dump_march_5th_2025.dump d7f4b709158e:/backup.dump
```

### 6. Restore inside docker

``` bash
docker exec -it d7f4b709158e mongorestore --gzip --archive=/backup.dump --nsInclude=vadio-staging.* --drop
```
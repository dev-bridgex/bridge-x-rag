// Switch to admin database and authenticate
db = db.getSiblingDB("admin");
db.auth(process.env.MONGODB_ROOT_USER, process.env.MONGODB_ROOT_PASSWORD);

// Switch to application database
db = db.getSiblingDB(process.env.MONGODB_DATABASE);

// Create application user
db.createUser({
    user: process.env.MONGODB_USERNAME,
    pwd: process.env.MONGODB_PASSWORD,
    roles: [
      'readWrite'
    ]
});

// Create collections for the application
db.createCollection('knowledge_bases');
db.createCollection('assets');
db.createCollection('chunks');

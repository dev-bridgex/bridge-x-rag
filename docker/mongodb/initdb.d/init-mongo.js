// Switch to admin database and authenticate
db = db.getSiblingDB("admin");
db.auth('admin', 'admin'); // Requires admin user with proper privileges [[9]]

// Switch to target database
db = db.getSiblingDB('mini-rag');

// Create user with proper syntax (role as string)
db.createUser({
    user: "bazoo",
    pwd: "Daf28876#@",
    roles: [
      'readWrite' // Role format simplified [[1]][[3]][[7]]
    ]
});

// Create collection (requires valid user permissions)
db.createCollection('test_docker');
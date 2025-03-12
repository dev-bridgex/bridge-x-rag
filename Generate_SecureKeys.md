# For JWT Keys (SECRET_KEY and REFRESH_SECRET_KEY)
Using OpenSSL:

``` bash

# Generate SECRET_KEY
openssl rand -base64 32

# Generate REFRESH_SECRET_KEY
openssl rand -base64 32

```
# For Encryption Key (ENCRYPTION_KEY)

``` bash

# Generate a 32-byte key for AES-GCM
openssl rand -base64 32 | tr -d '\n' | tr '+/' '-_' | tr -d '='

```
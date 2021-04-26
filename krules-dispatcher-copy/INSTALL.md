## OSX


```
# pyurl needs ssl libs
brew install openssl
export LIBRARY_PATH=/usr/local/opt/openssl/lib
export CPATH=/usr/local/opt/openssl/include
export  PYCURL_SSL_LIBRARY="openssl"
```
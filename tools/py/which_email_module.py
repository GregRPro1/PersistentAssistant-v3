import email, sys, ssl
print('email module file:', getattr(email, '__file__', '<built-in>'))
print('python:', sys.version)
print('openssl:', ssl.OPENSSL_VERSION)
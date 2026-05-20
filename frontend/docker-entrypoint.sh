#!/bin/sh
# Generate runtime env.js

echo "window.ENV = {" > /usr/share/nginx/html/env.js
echo "  VITE_API_BASE_URL: '${VITE_API_BASE_URL}'" >> /usr/share/nginx/html/env.js
echo "};" >> /usr/share/nginx/html/env.js

exec "$@"

#!/bin/sh
# Generate runtime env.js

echo "window.ENV = {" > /tmp/env.js
echo "  VITE_API_BASE_URL: '${VITE_API_BASE_URL}'" >> /tmp/env.js
echo "};" >> /tmp/env.js

exec "$@"

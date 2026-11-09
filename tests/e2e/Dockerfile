FROM node:24-bookworm-slim
WORKDIR /qa
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts --no-fund --no-audit \
    && npx playwright install --with-deps chromium
COPY playwright.config.js ./
COPY tests/e2e ./tests/e2e
CMD ["npm", "run", "test:app"]

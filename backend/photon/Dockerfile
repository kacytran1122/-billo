FROM node:22-slim

ENV NODE_ENV=production

WORKDIR /app/backend/photon

COPY backend/photon/package.json backend/photon/package-lock.json ./
RUN npm ci && npm cache clean --force

COPY backend/photon/tsconfig.json ./
COPY backend/photon/src ./src

RUN chown -R node:node /app
USER node

EXPOSE 3000
CMD ["npm", "start"]

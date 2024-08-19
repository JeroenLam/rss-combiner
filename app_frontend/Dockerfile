# Stage 1: Build JS
FROM node:current-alpine AS build

WORKDIR /usr/app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run

# Stage 2: Start server
FROM nginx:alpine
COPY --from=build /usr/app/dist /usr/share/nginx/html/dist
ADD . /usr/share/nginx/html
EXPOSE 80
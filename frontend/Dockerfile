FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Allow API URL to be injected at build time.
# Dev: not used here (dev server reads env at runtime)
# Local prod test: set to http://localhost:8010
# Production server: leave empty — nginx proxies /api/ to backend
ARG NEXT_PUBLIC_API_URL=
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN npm run build

EXPOSE 3001

CMD ["npm", "start", "--", "-p", "3001"]

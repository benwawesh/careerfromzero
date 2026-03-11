FROM node:20-alpine

# Set work directory
WORKDIR /app

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy project
COPY . .

# Build Next.js app
RUN npm run build

# Expose port
EXPOSE 3001

# Start Next.js
CMD ["npm", "start", "--", "-p", "3001"]

FROM node:22.13.1-alpine AS build

# WORKDIR /app/frontend
# COPY BadmintonSystem.FE/package.json BadmintonSystem.FE/package-lock.json ./

# RUN npm install -g npm@latest
# RUN npm install
# COPY BadmintonSystem.FE/ ./ 

# RUN npm install -g @angular/cli 
# RUN ng build


FROM nginx:alpine AS nginx

RUN rm -rf /usr/share/nginx/html/*
# COPY --from=build ./Frontend/Build /usr/share/nginx/html
COPY ./Frontend/Build /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

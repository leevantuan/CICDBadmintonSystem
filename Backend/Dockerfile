# FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS base
# USER $APP_UID
# WORKDIR /app
# EXPOSE 8080
# EXPOSE 8081

# FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
# ARG BUILD_CONFIGURATION=Release
# WORKDIR /src
# COPY ["BadmintonSystem.BE/src/BadmintonSystem.API/BadmintonSystem.API.csproj", "src/BadmintonSystem.API/"]
# COPY ["BadmintonSystem.BE/src/BadmintonSystem.Application/BadmintonSystem.Application.csproj", "src/BadmintonSystem.Application/"]
# COPY ["BadmintonSystem.BE/src/BadmintonSystem.Contract/BadmintonSystem.Contract.csproj", "src/BadmintonSystem.Contract/"]
# COPY ["BadmintonSystem.BE/src/BadmintonSystem.Domain/BadmintonSystem.Domain.csproj", "src/BadmintonSystem.Domain/"]
# COPY ["BadmintonSystem.BE/src/BadmintonSystem.Persistence/BadmintonSystem.Persistence.csproj", "src/BadmintonSystem.Persistence/"]
# COPY ["BadmintonSystem.BE/src/BadmintonSystem.Infrastructure.Dapper/BadmintonSystem.Infrastructure.Dapper.csproj", "src/BadmintonSystem.Infrastructure.Dapper/"]
# COPY ["BadmintonSystem.BE/src/BadmintonSystem.Infrastructure.Bus/BadmintonSystem.Infrastructure.Bus.csproj", "src/BadmintonSystem.Infrastructure.Bus/"]
# COPY ["BadmintonSystem.BE/src/BadmintonSystem.Infrastructure/BadmintonSystem.Infrastructure.csproj", "src/BadmintonSystem.Infrastructure/"]
# COPY ["BadmintonSystem.BE/src/BadmintonSystem.Presentation/BadmintonSystem.Presentation.csproj", "src/BadmintonSystem.Presentation/"]
# RUN dotnet restore "src/BadmintonSystem.API/BadmintonSystem.API.csproj"
# COPY ./BadmintonSystem.BE/ /app/

# WORKDIR "/app/src/BadmintonSystem.API"
# RUN dotnet build "BadmintonSystem.API.csproj" -c $BUILD_CONFIGURATION -o /app/build

# FROM build AS publish
# ARG BUILD_CONFIGURATION=Release
# RUN dotnet publish "BadmintonSystem.API.csproj" -c $BUILD_CONFIGURATION -o /app/publish /p:UseAppHost=false

# FROM mcr.microsoft.com/dotnet/aspnet:8.0-alpine AS final
# WORKDIR /app
# COPY --from=publish /app/publish .

# RUN find /app -name "*.pdb" -delete

# ENTRYPOINT ["dotnet", "BadmintonSystem.API.dll"]

# Use the base image for the runtime environment
FROM mcr.microsoft.com/dotnet/aspnet:8.0-alpine
WORKDIR /src
EXPOSE 5000

# Use the SDK image for building the application
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build 

# # Copy the backend build folder into the container
COPY ./Backend/Build .

# Run the application with the specified environment
# ENTRYPOINT ["dotnet", "BadmintonSystem.API.dll", "--environment", "Development", "--urls", "http://*:5000"]

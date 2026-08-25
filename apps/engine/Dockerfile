FROM maven:3.9.11-eclipse-temurin-21 AS build

WORKDIR /build

COPY .mvn .mvn
COPY mvnw pom.xml ./
RUN chmod +x mvnw && ./mvnw -B -ntp dependency:go-offline

COPY src ./src
RUN ./mvnw -B -ntp package -DskipTests

FROM eclipse-temurin:21-jre-alpine AS runtime

RUN addgroup -S servicerswitch && adduser -S servicerswitch -G servicerswitch
USER servicerswitch

WORKDIR /service
COPY --from=build /build/target/engine-0.1.0.jar app.jar

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "/service/app.jar"]

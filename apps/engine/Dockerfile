FROM maven:3.9.11-eclipse-temurin-21 AS build

WORKDIR /build

COPY pom.xml ./
RUN mvn -B -ntp dependency:go-offline

COPY src ./src
RUN mvn -B -ntp package -DskipTests

FROM eclipse-temurin:21-jre-alpine AS runtime

RUN addgroup -S servicerswitch && adduser -S servicerswitch -G servicerswitch
USER servicerswitch

WORKDIR /service
COPY --from=build /build/target/engine-0.1.0.jar app.jar

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "/service/app.jar"]

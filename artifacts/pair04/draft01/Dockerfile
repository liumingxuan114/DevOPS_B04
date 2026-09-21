FROM eclipse-temurin:11-jdk-jammy
WORKDIR /workspace
COPY . .
RUN ./mvnw -B -DskipTests package
CMD ["java", "-jar", "target/app.jar"]

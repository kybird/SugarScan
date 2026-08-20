allprojects {
    repositories {
        google()
        mavenCentral()
    }
}

val newBuildDir: Directory =
    rootProject.layout.buildDirectory
        .dir("../../build")
        .get()
rootProject.layout.buildDirectory.value(newBuildDir)

subprojects {
    val newSubprojectBuildDir: Directory = newBuildDir.dir(project.name)
    project.layout.buildDirectory.value(newSubprojectBuildDir)
}
// AGP 9 는 한 모듈 안에서 Java 와 Kotlin 의 JVM 타깃이 다르면 빌드를 멈춘다.
// 일부 플러그인(tflite_flutter 등)이 Java 만 11 로 못박고 Kotlin 은 지정하지
// 않아 툴체인 기본값(21)이 잡히면서 어긋난다. 앱과 같은 17 로 통일한다.
subprojects {
    // afterEvaluate 여야 한다. 플러그인들이 자기 build.gradle 에서 Java 11 을
    // 지정하는데, 그 설정이 여기보다 늦게 적용되어 앞선 값을 덮어쓴다.
    afterEvaluate {
        extensions.findByType<com.android.build.gradle.LibraryExtension>()
            ?.compileOptions {
                sourceCompatibility = JavaVersion.VERSION_17
                targetCompatibility = JavaVersion.VERSION_17
            }
        tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinJvmCompile>()
            .configureEach {
                compilerOptions.jvmTarget.set(
                    org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17,
                )
            }
    }
}

subprojects {
    project.evaluationDependsOn(":app")
}

tasks.register<Delete>("clean") {
    delete(rootProject.layout.buildDirectory)
}

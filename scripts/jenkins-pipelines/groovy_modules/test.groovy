def setupTestEnv(String buildMode, String architecture=generalProperties.x86ArchName, boolean dryRun=false, String scyllaVersion, String scyllaRelease) {
	// This override of HOME as an empty dir is needed by ccm
	echo "Setting test environment, mode: |$buildMode|, architecture: |$architecture|"
	def homeDir="$WORKSPACE/cluster_home"
	createEmptyDir(homeDir)
	unifiedPackageName = artifact.relocUnifiedPackageName (
		dryRun: dryRun,
		checkLocal: true,
		mustExist: false,
		urlOrPath: "$WORKSPACE/${gitProperties.scyllaCheckoutDir}/build/$buildMode/dist/tar",
		buildMode: buildMode,
		architecture: architecture,
	)

	String scyllaUnifiedPkgFile = "$WORKSPACE/${gitProperties.scyllaCheckoutDir}/build/$buildMode/dist/tar/${unifiedPackageName}"
	echo "Test will use package: $scyllaUnifiedPkgFile"
	boolean pkgFileExists = fileExists scyllaUnifiedPkgFile
	env.NODE_INDEX = generalProperties.smpNumber
	env.SCYLLA_VERSION = artifactScyllaVersion()
	if (!env.MAPPED_SCYLLA_VERSION && !general.versionFormatOK(env.SCYLLA_VERSION)) {
		env.MAPPED_SCYLLA_VERSION = "999.99.0"
	}
	env.EVENT_LOOP_MANAGER = "asyncio"
	// Some tests need event loop, 'asyncio' is most tested, so let's use it
	env.SCYLLA_UNIFIED_PACKAGE = scyllaUnifiedPkgFile
	env.DTEST_REQUIRE = "${branchProperties.dtstRequireValue}" // Could be empty / not exist
}

def createEmptyDir(String path) {
	sh "rm -rf $path && mkdir -p $path"
}

def artifactScyllaVersion() {
	def versionFile = generalProperties.buildMetadataFile
	def scyllaSha = ""
	boolean versionFileExists = fileExists "${versionFile}"
	if (versionFileExists) {
		scyllaSha = sh(script: "awk '/scylladb\\/scylla(-enterprise)?\\.git/ { print \$NF }' ${generalProperties.buildMetadataFile}", returnStdout: true).trim()
	}
	echo "Version is: |$scyllaSha|"
	return scyllaSha
}

def doRustDriverTest (Map args) {
	// Run the Rust test upon different repos
	// Parameters:
	// boolean (default false): dryRun - Run builds on dry run (that will show commands instead of really run them).
	// string (mandatory): rustDriverScyllaCheckoutDir - Scylla checkout dir
	// string (mandatory): rustDriverMatrixCheckoutDir - The general rust driver matrix dir
	// String (mandatory): driverType - scylla
	// String (mandatory): rustDriverVersions - rust driver versions to check
	// String (mandatory): cqlBinaryProtocols - CQL Binary Protocols
	// String (default: x86_64): architecture Which architecture to publish x86_64|aarch64


	general.traceFunctionParams ("test.doRustDriverTest", args)
	general.errorMissingMandatoryParam ("test.doRustDriverTest",
		[rustDriverScyllaCheckoutDir: "$args.rustDriverScyllaCheckoutDir",
		 rustDriverMatrixCheckoutDir: "$args.rustDriverMatrixCheckoutDir",
		 driverType: "$args.driverType",
		 rustDriverVersions: "$args.rustDriverVersions",
		])

	boolean dryRun = args.dryRun ?: false
	String architecture = args.architecture ?: generalProperties.x86ArchName

	setupTestEnv("release", architecture, dryRun, args.scyllaVersion, args.scyllaRelease)
	String rustParams = "python3 main.py $args.rustDriverScyllaCheckoutDir"
	rustParams += " --test-type $args.testType"
	rustParams += " --tests tests/integration/standard"
	rustParams += " --versions $args.rustDriverVersions"
	if (args.email_recipients?.trim()) {
		rustParams += " --recipients $args.email_recipients"
	}

	dir(args.rustDriverMatrixCheckoutDir) {
		general.runOrDryRunSh (dryRun, "$args.rustDriverMatrixCheckoutDir/scripts/run_test.sh $rustParams", "Run Rust Driver Matrix test")
	}
}

return this

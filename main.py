import sys
import argparse
import logging
import os
import subprocess
from datetime import timedelta
from typing import List
import traceback

# from common import run_command_in_shell, CCM_CLUSTER_IP_PREFIX, CCM_CLUSTER_NODES
from run import Run
from email_sender import create_report, get_driver_origin_remote, send_mail

logging.basicConfig(level=logging.INFO)


class EmptyTestResult(Exception):
    pass


def main(arguments: argparse.Namespace):
    status = 0
    results = dict()
    # TODO: move docker configure to rust-driver-matrix-test.jenkinsfile
    # Start docker configure
    # run_command_in_shell(driver_repo_path=arguments.rust_driver_git,
    #                      cmd=f"pip3 install https://github.com/scylladb/scylla-ccm/archive/master.zip")
    # run_command_in_shell(driver_repo_path=arguments.rust_driver_git,
    #                      cmd=f"ln -s /usr/local/bin/ccm /bin/ccm")
    # run_command_in_shell(driver_repo_path=arguments.rust_driver_git,
    #                      cmd=f"ccm create -i {CCM_CLUSTER_IP_PREFIX}. -n {CCM_CLUSTER_NODES} --scylla -v "
    #                          f"{arguments.scylla_version} scylla-cluster")
    # run_command_in_shell(driver_repo_path=arguments.rust_driver_git,
    #                      cmd=f"ccm start")
    # Finish docker configure

    for driver_version in arguments.versions:
        results[driver_version] = dict()
        for test in arguments.tests:
            logging.info('=== RUST DRIVER VERSION %s. TEST: %s ===', driver_version, test)
            try:
                report = Run(rust_driver_git=arguments.rust_driver_git,
                             tag=driver_version,
                             test=test,
                             scylla_version=arguments.scylla_version).call_test_func()

                if not report:
                    raise EmptyTestResult(f"No result for test '{test}' and driver version {driver_version}")

                logging.info("=== RUST DRIVER MATRIX RESULTS FOR DRIVER VERSION %s ===", driver_version)
                logging.info("\n".join(f"{key}: {value}" for key, value in report.summary.items()))
                if report.is_failed:
                    status = 1
                results[driver_version][test] = report.summary
                results[driver_version][test]['time'] = \
                    str(timedelta(seconds=results[driver_version][test]['testsuite_summary']['time']))[:-3]
            except Exception:
                logging.exception(f"{driver_version} failed")
                status = 1
                exc_type, exc_value, exc_traceback = sys.exc_info()
                results[driver_version] = dict(exception=traceback.format_exception(exc_type, exc_value, exc_traceback))

    if arguments.recipients:
        email_report = create_report(results=results)
        email_report['driver_remote'] = get_driver_origin_remote(arguments.rust_driver_git)
        email_report['status'] = "SUCCESS" if status == 0 else "FAILED"
        send_mail(arguments.recipients, email_report)

    quit(status)


def extract_n_latest_repo_tags(repo_directory: str, major_versions: List[str], latest_tags_size: int = 2) -> List[str]:
    major_versions = sorted(major_versions, key=lambda major_ver: major_ver)
    commands = [f"cd {repo_directory}", "git checkout .", ]
    # if not os.environ.get("DEV_MODE", False):
    #     commands.append("git fetch -p --all")
    commands.append("git tag --sort=-creatordate | grep v0\.")

    selected_tags = {}
    ignore_tags = set()
    result = []
    commands_in_line = "\n".join(commands)
    try:
        lines = subprocess.check_output(commands_in_line, shell=True, stderr=subprocess.STDOUT).decode().splitlines()
    except subprocess.CalledProcessError as e:
        raise RuntimeError("command '{}' return with error (code {}): {}".format(e.cmd, e.returncode, e.output))

    for repo_tag in lines:
        if "." in repo_tag:
            version = tuple(repo_tag.split(".", maxsplit=2)[:2])
            if version not in ignore_tags:
                ignore_tags.add(version)
                selected_tags.setdefault(version, []).append(repo_tag)

    for major_version in major_versions:
        if len(selected_tags[major_version]) < latest_tags_size:
            raise ValueError(f"There are no '{latest_tags_size}' different versions that start with the major version"
                             f" '{major_version}'")
        result.extend(selected_tags[major_version][:latest_tags_size])
    return result


def get_arguments() -> argparse.Namespace:
    versions = ['v0.8.2', 'v0.7.0']
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('rust_driver_git', help='folder with git repository of rust-driver')
    parser.add_argument('--versions', default=versions,
                        help='rust-driver versions to test, default={}'.format(','.join(versions)))
    parser.add_argument('--tests', choices=['rust', 'serverless', 'tls'], defaults='rust', nargs='*', type=str,
                        help='tests to run')
    parser.add_argument('--scylla-version', help="relocatable scylla version to use",
                        default=os.environ.get('SCYLLA_VERSION', None)),
    parser.add_argument('--version-size', help='The number of the latest versions that will test.'
                                               'The version is filtered by the major and minor values.'
                                               'For example, the user selects the 2 latest versions for version 4.'
                                               'The values to be returned are: 4.9.0-scylla-1 and 4.8.0-scylla-0',
                        type=int, default=None, nargs='?')
    parser.add_argument('--recipients', help="whom to send mail at the end of the run",  nargs='+', default=None)
    arguments = parser.parse_args()
    versions = arguments.versions
    if not isinstance(versions, list):
        versions = versions.split(',')

    arguments.versions = versions

    if arguments.version_size:
        arguments.versions = extract_n_latest_repo_tags(repo_directory=arguments.rust_driver_git,
                                                        major_versions=list({tuple(v.split('.', maxsplit=2)[:2]) for v in versions}),
                                                        latest_tags_size=arguments.version_size)

    return arguments


if __name__ == '__main__':
    main(get_arguments())

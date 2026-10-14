"""Isolated Windows build bootstrap. Python standard library only."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent
WORK = ROOT / 'work'
SOURCE = WORK / 'pcsx2'
COMMIT = 'e35cb2c87590bc3d127b3bb4dd222b01e598c9a4'
DEPS_SHA = 'a3133c7841e8fbdab6f4d1d5ad8efec31fb1ecda95ffed39f4d1f36bb7eb0007'
FFMPEG_SHA = 'c4f8a5093997445fbb08c694be289b36eed660e46e02078d9371a2481453ae5a'
RELEASES = 'https://github.com/PCSX2/pcsx2-windows-dependencies/releases/download/'
ENV = os.environ.copy()
LOG = None


def say(message):
    print(message, flush=True)
    if LOG:
        LOG.write(message + '\n')
        LOG.flush()


def run(args, cwd=ROOT):
    args = [str(a) for a in args]
    say('\n> ' + subprocess.list2cmdline(args))
    with subprocess.Popen(args, cwd=cwd, env=ENV, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True,
                          encoding='utf-8', errors='replace') as process:
        for line in process.stdout:
            say(line.rstrip())
        if process.wait():
            raise RuntimeError('Command failed. See the output above.')


def capture(args):
    args = [str(a) for a in args]
    result = subprocess.run(args, env=ENV, capture_output=True,
                            text=True, encoding='utf-8', errors='replace')
    if result.returncode:
        say('\n> ' + subprocess.list2cmdline(args))
        if result.stdout:
            say(result.stdout.rstrip())
        if result.stderr:
            say(result.stderr.rstrip())
        result.check_returncode()
    return result.stdout.strip()


def verify_checkout(git, source=SOURCE, expected_commit=COMMIT,
                    expected_origin='https://github.com/PCSX2/pcsx2.git'):
    try:
        commit = capture([git, '-C', source, 'rev-parse', 'HEAD'])
    except subprocess.CalledProcessError as error:
        if 'detected dubious ownership in repository' not in (error.stderr or ''):
            raise
        if not (source / '.git').is_dir():
            raise RuntimeError('Expected an ordinary Git checkout in the build folder.')
        # Trust only this build checkout, only for this process and its children.
        # Never write global Git configuration or use a wildcard safe.directory.
        count = int(ENV.get('GIT_CONFIG_COUNT', '0'))
        ENV['GIT_CONFIG_KEY_' + str(count)] = 'safe.directory'
        ENV['GIT_CONFIG_VALUE_' + str(count)] = source.resolve().as_posix()
        ENV['GIT_CONFIG_COUNT'] = str(count + 1)
        say('Git reported an ownership mismatch. Retrying with trust limited to this build checkout.')
        commit = capture([git, '-C', source, 'rev-parse', 'HEAD'])
    origin = capture([git, '-C', source, 'config', '--get', 'remote.origin.url'])
    if origin != expected_origin or commit != expected_commit:
        raise RuntimeError('Unexpected source origin or commit. Refusing to change this checkout.')


def digest(path):
    with open(path, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def download(url, path, expected):
    if path.exists() and digest(path) == expected:
        say('Using verified download: ' + path.name)
        return
    say('Downloading ' + path.name + ' (this may take a few minutes)...')
    partial = path.with_suffix('.partial')
    request = urllib.request.Request(url, headers={'User-Agent': 'PCSX2-AutoBIOS-BuildKit/1'})
    with urllib.request.urlopen(request, timeout=120) as response, open(partial, 'wb') as out:
        shutil.copyfileobj(response, out)
    if digest(partial) != expected:
        raise RuntimeError('Download hash changed for ' + path.name +
                           '. No changed dependency will be used. Send Build.log for an updated kit.')
    partial.replace(path)


def find_tool(name, candidates=()):
    found = shutil.which(name, path=ENV.get('PATH'))
    if found:
        return Path(found)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise RuntimeError('Required tool not found: ' + name)


def select_cmake(vs):
    bundled = Path(vs) / 'Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe'
    if bundled.is_file() and bundled.with_name('cmcldeps.exe').is_file():
        say('Using Visual Studio bundled CMake: ' + str(bundled))
        return bundled
    # A complete portable distribution, independent of tools belonging to other apps.
    WORK.mkdir(exist_ok=True)
    archive = WORK / 'cmake-3.31.6-windows-x86_64.zip'
    expected = 'd163cd3ab4959b0a53fa8988f2ddbd2e6c501658201e6a154386bad9dbe4f836'
    download('https://github.com/Kitware/CMake/releases/download/v3.31.6/' + archive.name,
             archive, expected)
    with zipfile.ZipFile(archive) as z:
        z.extractall(WORK / 'tools')
    cmake = WORK / 'tools/cmake-3.31.6-windows-x86_64/bin/cmake.exe'
    if not cmake.is_file() or not cmake.with_name('cmcldeps.exe').is_file():
        raise RuntimeError('The portable CMake package is missing its resource compiler helper.')
    say('Using complete portable CMake: ' + str(cmake))
    return cmake


SHADER_COMMIT = '2ec856ffec9bb369bccf82cfb4bc587d38821105'
SHADER_FILES = ['ShaderGlass/WinMain.cpp', 'ShaderGlass/PrototypeReady.h',
    'ShaderGlass/CaptureManager.cpp', 'ShaderGlass/ShaderGlass.cpp',
    'ShaderGlass/ShaderGlass.h', 'ShaderGlass/ShaderGlass.vcxproj']


def prepare_shader(git):
    source = WORK / 'ShaderGlass'
    if not source.exists():
        run([git, '-c', 'core.autocrlf=false', 'clone', '--depth', '1', '--branch', 'v1.3.0',
             'https://github.com/mausimus/ShaderGlass.git', source])
    verify_checkout(git, source, SHADER_COMMIT, 'https://github.com/mausimus/ShaderGlass.git')
    return source


def save_shader_stamp(source):
    (WORK / 'shader-source-state.json').write_text(json.dumps({f: digest(source / f) for f in SHADER_FILES}, indent=2))


def verify_shader_stamp(source):
    for name, expected in json.loads((WORK / 'shader-source-state.json').read_text()).items():
        if digest(source / name) != expected:
            raise RuntimeError('Modified ShaderGlass source: ' + name)



def main():
    global ENV
    if os.name != 'nt':
        raise RuntimeError('Run Build.cmd on Windows with Visual Studio 2022 installed.')
    if '(' in str(ROOT) or ')' in str(ROOT) or len(str(ROOT)) > 85:
        raise RuntimeError('Extract the kit to a short path such as D:\\PCSX2Build (no parentheses).')
    import assemble
    say('Custom PCSX2 Nightly ' + assemble.VERSION + ' candidate1; ' + COMMIT)
    assemble.check_inputs(ROOT)
    say('Python: ' + sys.version.split()[0])
    vswhere = Path(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')) / 'Microsoft Visual Studio/Installer/vswhere.exe'
    vs = capture([vswhere, '-latest', '-version', '[17.0,18.0)', '-products', '*',
                  '-requires', 'Microsoft.VisualStudio.Component.VC.Tools.x86.x64',
                  '-property', 'installationPath'])
    if not vs:
        raise RuntimeError('Visual Studio 2022 with x64 C++ tools was not found.')
    say('Visual Studio: ' + vs)
    vcvars = Path(vs) / 'VC/Auxiliary/Build/vcvars64.bat'
    # Import the developer environment only into this build process. Never log it.
    comspec = os.environ.get('COMSPEC', r'C:\Windows\System32\cmd.exe')
    # cmd.exe does not use the C runtime's backslash-quote escaping rules.
    command = f'"{comspec}" /d /s /c "call "{vcvars}" >nul && set"'
    raw = subprocess.check_output(command, text=True, errors='replace')
    ENV = dict(line.split('=', 1) for line in raw.splitlines() if '=' in line and not line.startswith('='))
    # Windows env keys are case insensitive, Python dict keys are not.
    ENV = {key.upper(): value for key, value in ENV.items()}
    cmake_base = Path(vs) / 'Common7/IDE/CommonExtensions/Microsoft/CMake'
    extra = Path.home() / '.local/share/retcomm/toolchains/cmake-clang-v1/latest/bin'
    cmake = select_cmake(vs)
    ninja = find_tool('ninja.exe', [cmake_base / 'Ninja/ninja.exe', extra / 'ninja.exe'])
    git = find_tool('git.exe', [Path(r'C:\Program Files\Git\cmd\git.exe')])
    seven = find_tool('7z.exe', [Path(r'C:\Program Files\7-Zip\7z.exe')])
    compiler = find_tool('cl.exe')
    ENV['PATH'] = os.pathsep.join([str(git.parent), str(cmake.parent), str(ninja.parent), ENV['PATH']])
    run([cmake, '--version'])
    run([git, '--version'])
    WORK.mkdir(exist_ok=True)
    # A previous patch attempt can fail before writing its completion stamp.
    # Preserve that entire checkout instead of modifying or resetting it.
    if SOURCE.exists() and not (WORK / 'patched-files.json').exists():
        verify_checkout(git)
        if capture([git, '-C', SOURCE, 'status', '--porcelain']):
            backup = WORK / 'pcsx2-incomplete-backup'
            suffix = 1
            while backup.exists():
                backup = WORK / ('pcsx2-incomplete-backup-' + str(suffix))
                suffix += 1
            SOURCE.rename(backup)
            say('Preserved incomplete source checkout: ' + str(backup))
            say('Creating a fresh pinned checkout; existing dependency downloads are retained.')
    if not SOURCE.exists():
        run([git, '-c', 'core.autocrlf=false', 'clone', '--depth', '1', '--branch', assemble.TAG,
             'https://github.com/PCSX2/pcsx2.git', SOURCE])
    verify_checkout(git)
    shader_source = prepare_shader(git)
    patch_stamp = WORK / 'patched-files.json'
    if not patch_stamp.exists():
        if capture([git, '-C', SOURCE, 'status', '--porcelain', '--untracked-files=no']):
            raise RuntimeError('Source already has changes but no patch stamp. Send Build.log.')
        run([sys.executable, ROOT / 'verify-upstream.py', SOURCE])
        run([sys.executable, ROOT / 'autobios-test/apply-patch.py', SOURCE])
        # This custom build must not replace itself with an official update.
        updater = SOURCE / 'pcsx2-qt/AutoUpdaterDialog.cpp'
        original = updater.read_text(encoding='utf-8')
        needle = 'bool AutoUpdaterDialog::isSupported()\n{'
        if original.count(needle) != 1:
            raise RuntimeError('Unexpected updater source.')
        updater.write_text(original.replace(needle, needle + '\n\treturn false; // Custom build: updates are supplied by the component installer.\n'), encoding='utf-8', newline='\n')
        run([sys.executable, ROOT / 'apply-shader-patch.py', SOURCE, shader_source])
        run([sys.executable, ROOT / 'apply-sorting-patch.py', SOURCE])
        files = list(json.loads((ROOT / 'autobios-test/upstream-sha256.json').read_text()))
        files += ['pcsx2/AutoBios.h', 'pcsx2/AutoBiosPolicy.h', 'pcsx2/AutoBiosIdentity.h', 'pcsx2-qt/AutoUpdaterDialog.cpp']
        files += ['pcsx2-qt/MainWindow.cpp', 'pcsx2-qt/DisplayWidget.cpp', 'pcsx2-qt/QtHost.cpp', 'pcsx2-qt/ShaderPrototype.h']
        files += ['pcsx2/GameList.h', 'pcsx2/GameList.cpp', 'pcsx2-qt/Settings/GameSummaryWidget.cpp', 'pcsx2-qt/MainWindow.h', 'pcsx2-qt/GameList/GameListWidget.h', 'pcsx2-qt/GameList/GameListWidget.cpp']
        save_shader_stamp(shader_source)
        patch_stamp.write_text(json.dumps({name: digest(SOURCE / name) for name in files}, indent=2))
    else:
        for name, expected in json.loads(patch_stamp.read_text()).items():
            if digest(SOURCE / name) != expected:
                raise RuntimeError('Patched source was changed: ' + name)
    verify_shader_stamp(shader_source)
    # Accepted ShaderGlass worker is reused unchanged from the disposable install copy.
    run([compiler, '/nologo', '/std:c++17', '/EHsc', ROOT / 'autobios-test/tests/policy.cpp',
         '/Fe:' + str(WORK / 'policy-test.exe'), '/Fo:' + str(WORK / 'policy-test.obj')])
    run([WORK / 'policy-test.exe'])
    archive = WORK / 'windows-deps.7z'
    download(RELEASES + 'latest-windows-dependencies/pcsx2-windows-dependencies.7z', archive, DEPS_SHA)
    deps_stamp = WORK / 'deps-ready.txt'
    if not deps_stamp.exists() or deps_stamp.read_text() != DEPS_SHA:
        run([seven, 'x', '-y', '-o' + str(SOURCE), archive])
        deps_stamp.write_text(DEPS_SHA)
    ffmpeg = WORK / 'ffmpeg8.7z'
    download(RELEASES + 'FFMPEG/ffmpeglibs-8.0.7z', ffmpeg, FFMPEG_SHA)
    ffmpeg_dir = WORK / 'ffmpeg8'
    run([seven, 'x', '-y', '-o' + str(ffmpeg_dir), ffmpeg])
    # Exercise the actual RC command before resuming the large emulator build.
    probe = WORK / 'rc-probe'
    probe.mkdir(exist_ok=True)
    (probe / 'CMakeLists.txt').write_text(
        'cmake_minimum_required(VERSION 3.16)\nproject(ResourceCheck LANGUAGES CXX RC)\n'
        'add_library(resourcecheck OBJECT probe.rc)\n', encoding='utf-8')
    (probe / 'probe.rc').write_text('1 RCDATA { 0 }\n', encoding='ascii')
    cmcldeps = '-DCMAKE_CMCLDEPS_EXECUTABLE=' + str(cmake.with_name('cmcldeps.exe'))
    run([cmake, '-S', probe, '-B', WORK / 'rc-probe-build', '-G', 'Ninja',
         '-DCMAKE_MAKE_PROGRAM=' + str(ninja), '-DCMAKE_CXX_COMPILER=' + str(compiler), cmcldeps])
    run([cmake, '--build', WORK / 'rc-probe-build'])
    build = WORK / 'build'
    run([cmake, '-S', SOURCE, '-B', build, '-G', 'Ninja',
         cmcldeps,
         '-DCMAKE_MAKE_PROGRAM=' + str(ninja), '-DCMAKE_C_COMPILER=' + str(compiler),
         '-DCMAKE_CXX_COMPILER=' + str(compiler), '-DCMAKE_PREFIX_PATH=' + str(SOURCE / 'deps'),
         '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_INTERPROCEDURAL_OPTIMIZATION=ON',
         '-DDISABLE_ADVANCE_SIMD=ON', '-DENABLE_QT_UI=ON'])
    run([cmake, '--build', build, '--config', 'Release', '--parallel', str(min(12, os.cpu_count() or 4))])
    run([cmake, '--install', build, '--config', 'Release'])
    stage = WORK / 'package'
    if stage.exists():
        shutil.rmtree(stage)  # Only this kit's generated staging directory.
    shutil.copytree(SOURCE / 'bin', stage, ignore=shutil.ignore_patterns(
        '*.pdb', '*.lib', '*.exp', '*.ilk', '*.iobj', '*.ipdb', '*.bsc', '.gitignore'))
    executable = stage / 'pcsx2-qt.exe'
    if not executable.is_file():
        raise RuntimeError('Expected compiled pcsx2-qt.exe is missing.')
    executable.rename(stage / 'PCSX2-ShaderPrototype.exe')
    # Include release DLLs, including transitive dependencies added to the prebuilt package.
    deps_bin = SOURCE / 'deps/bin'
    for dll in deps_bin.glob('*.dll'):
        if (dll.stem.startswith('Qt6') and dll.stem.endswith('d')) or dll.name == 'kddockwidgets-qt6d.dll':
            continue
        if dll.stem.startswith(('avcodec-', 'avformat-', 'avutil-', 'swresample-', 'swscale-')):
            continue
        shutil.copy2(dll, stage / dll.name)
    for dll in ffmpeg_dir.rglob('*.dll'):
        shutil.copy2(dll, stage / dll.name)
    # App-local Visual C++ runtime, from the installed redistributable directory.
    redist = Path(ENV.get('VCTOOLSREDISTDIR', str(Path(vs) / 'VC/Redist/MSVC')))
    runtime = list(redist.glob('x64/Microsoft.VC*.CRT/*.dll'))
    if not runtime:
        raise RuntimeError('Could not locate the x64 redistributable runtime in ' + str(redist))
    for dll in runtime:
        shutil.copy2(dll, stage / dll.name)
    (stage / 'portable.txt').write_text('../..\n', encoding='ascii')
    for name in ['QtPlugins/platforms/qwindows.dll', 'Qt6Core.dll', 'resources/GameIndex.yaml', 'avcodec-62.dll']:
        if not (stage / name).is_file():
            raise RuntimeError('Missing runtime file: ' + name)
    metadata = {'nightly_port': assemble.VERSION + '-candidate1', 'pcsx2_commit': COMMIT,
                'shaderglass_commit': SHADER_COMMIT,
                'dependencies_sha256': DEPS_SHA, 'ffmpeg_sha256': FFMPEG_SHA,
                'status': 'compiled; Windows acceptance tests required'}
    (stage / 'BUILD-INFO.json').write_text(json.dumps(metadata, indent=2))
    official = WORK / 'official-nightly'
    if official.exists():
        shutil.rmtree(official)  # Generated files inside this isolated kit only.
    run([seven, 'x', '-y', '-o' + str(official), ROOT / assemble.NIGHTLY])
    # Use the patch archive shipped with the selected nightly, not a moving URL.
    shutil.copy2(official / 'resources/patches.zip', stage / 'resources/patches.zip')
    assemble.package(ROOT, stage, official)
    say('SUCCESS: ' + assemble.RUNTIME_NAME)
    say('Review and test this runtime before signing an update package.')
    say('Output is not signed and cannot be installed through the controlled updater yet.')



if __name__ == '__main__':
    with open(ROOT / 'Build.log', 'w', encoding='utf-8', buffering=1) as LOG:
        try:
            main()
        except Exception:
            say('\nBUILD STOPPED\n' + traceback.format_exc())
            sys.exit(1)

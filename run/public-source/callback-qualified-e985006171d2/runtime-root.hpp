// Linux-only explicit runtime-root adaptation for pinned rAthena Core.
// Startup requires the caller's explicit --runtime-root directory selection.
#ifndef RATHENA_OFFLINE_RUNTIME_ROOT_HPP
#define RATHENA_OFFLINE_RUNTIME_ROOT_HPP
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

namespace runtime_root {
class OwnedFd {
    int fd_;
public:
    explicit OwnedFd(int fd = -1): fd_(fd) {}
    OwnedFd(const OwnedFd&) = delete;
    OwnedFd& operator=(const OwnedFd&) = delete;
    ~OwnedFd() { if (fd_ >= 0) { const int result = ::close(fd_); (void)result; } }
    int get() const { return fd_; }
    bool close_checked() {
        const int fd = fd_;
        fd_ = -1; // Linux close releases ownership even on EINTR: never retry.
        return fd < 0 || ::close(fd) == 0;
    }
    bool replace(int next) {
        if (next < 0) return false;
        if (!close_checked()) { const int result = ::close(next); (void)result; return false; }
        fd_ = next;
        return true;
    }
};

static bool literal_absolute(const char* path) {
    if (!path || path[0] != '/' || path[1] == '\0' || strlen(path) >= 4096) return false;
    const char* component = path + 1;
    for (const unsigned char* p = reinterpret_cast<const unsigned char*>(component); ; ++p) {
        if (*p == '/' || *p == '\0') {
            const size_t size = reinterpret_cast<const char*>(p) - component;
            if (size == 0 || (size == 1 && component[0] == '.') ||
                (size == 2 && component[0] == '.' && component[1] == '.')) return false;
            if (*p == '\0') return true;
            component = reinterpret_cast<const char*>(p) + 1;
        } else if (*p < 32 || *p > 126) return false;
    }
}

static bool open_literal_root(const char* path, OwnedFd& root) {
    if (!literal_absolute(path)) return false; // before any canonicalization/open
    if (!root.replace(::open("/", O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW))) return false;
    const char* component = path + 1;
    for (;;) {
        const char* end = strchr(component, '/');
        const std::string name(component, end ? static_cast<size_t>(end - component) : strlen(component));
        const int next = ::openat(root.get(), name.c_str(), O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
        if (!root.replace(next)) return false;
        if (!end) return true;
        component = end + 1;
    }
}

static bool same_inode(const struct stat& a, const struct stat& b) {
    return a.st_dev == b.st_dev && a.st_ino == b.st_ino;
}

static bool private_directory(const struct stat& info) {
    return S_ISDIR(info.st_mode) && info.st_uid == geteuid() && (info.st_mode & 07777) == 0700;
}

// Shared native CWD mechanism; diagnostics exit and explicit run mode continues.
// This is local caller trust, not an adversarial world-volume ownership claim.
static bool bind_runtime_root(const char* requested, struct stat& evidence) {
    OwnedFd root;
    if (!open_literal_root(requested, root) || fstat(root.get(), &evidence) != 0 ||
        !private_directory(evidence) || fchdir(root.get()) != 0) return false;
    OwnedFd relative(::open(".", O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW));
    struct stat cwd_info;
    if (relative.get() < 0 || fstat(relative.get(), &cwd_info) != 0 ||
        !same_inode(cwd_info, evidence) || !private_directory(cwd_info)) return false;
    char* cwd = getcwd(nullptr, 0);
    if (!cwd) return false;
    const bool spelling_matches = strcmp(cwd, requested) == 0;
    free(cwd);
    if (!spelling_matches) return false;
    // Reopen from '/' after fchdir: refuse renamed/replaced/aliased roots.
    OwnedFd rebound;
    struct stat path_info;
    if (!open_literal_root(requested, rebound) || fstat(rebound.get(), &path_info) != 0 ||
        !same_inode(path_info, evidence) || !private_directory(path_info)) return false;
    cwd = getcwd(nullptr, 0);
    if (!cwd) return false;
    const bool still_matches = strcmp(cwd, requested) == 0;
    free(cwd);
    if (!still_matches) return false;
    const bool rebound_closed = rebound.close_checked();
    const bool relative_closed = relative.close_checked();
    const bool root_closed = root.close_checked();
    return rebound_closed && relative_closed && root_closed;
}

static char* server_basename(char* argv0) {
    char* slash = strrchr(argv0, '/');
    return slash ? slash + 1 : argv0;
}

static bool known_name(const char* name) {
    return !strcmp(name, "login-server") || !strcmp(name, "char-server") || !strcmp(name, "map-server");
}

static int diagnostic(const char* requested, const char* server_name) {
    try {
        struct stat evidence;
        if (!known_name(server_name) || !bind_runtime_root(requested, evidence)) {
            fprintf(stderr, "rAthena: runtime root rejected; startup remains blocked.\n");
            return 2;
        }
        printf("{\"server_name\":\"%s\",\"root_bound\":true,\"cwd_matches\":true,\"relative_matches\":true,\"startup_blocked\":true,\"device\":%llu,\"inode\":%llu}\n",
            server_name, static_cast<unsigned long long>(evidence.st_dev), static_cast<unsigned long long>(evidence.st_ino));
        return 0;
    } catch (...) {
        // RAII releases owned descriptors; no cleanup exception replaces origin.
        fprintf(stderr, "rAthena: runtime root rejected; startup remains blocked.\n");
        return 2;
    }
}
// Only custom options are consumed here. Role-specific options retain their
// original native parser, reached after the explicit root is bound.
static int prepare(int& argc, char** argv, const char* server_name) {
    if (!known_name(server_name)) {
        fprintf(stderr, "rAthena: server basename rejected; startup remains blocked.\n");
        return 2;
    }
    if (argc == 2 && (!strcmp(argv[1], "--help") || !strcmp(argv[1], "--version"))) {
        printf("rAthena pinned e985006171d2eb320ee512a653f4c83aea3d81b6 MAIN/pre-re PACKETVER=20180704\n");
        printf("Safe diagnostics: --help | --version | --check-runtime-root ABS.\n");
        printf("Native startup requires --runtime-root ABS (same-UID 0700 directory).\n");
        printf("Diagnostics are not world validation.\n");
        return 0;
    }
    if (argc == 3 && !strcmp(argv[1], "--check-runtime-root")) {
        return diagnostic(argv[2], server_name);
    }
    int index = -1;
    for (int i = 1; i < argc; ++i) {
        if (!strcmp(argv[i], "--runtime-root")) {
            if (index != -1 || i + 1 >= argc || argv[i + 1][0] == '-') {
                fprintf(stderr, "rAthena: runtime arguments rejected; startup remains blocked.\n");
                return 2;
            }
            index = i;
            ++i;
        } else if (!strncmp(argv[i], "--runtime-root", 14) ||
                   !strncmp(argv[i], "--check-", 8) ||
                   !strcmp(argv[i], "--help") || !strcmp(argv[i], "--version")) {
            fprintf(stderr, "rAthena: runtime arguments rejected; startup remains blocked.\n");
            return 2;
        }
    }
    if (index == -1) {
        fprintf(stderr, "rAthena: explicit --runtime-root required; startup remains blocked.\n");
        return 78;
    }
    const char* requested = argv[index + 1];
    try {
        struct stat evidence;
        if (!bind_runtime_root(requested, evidence)) {
            fprintf(stderr, "rAthena: runtime root rejected; startup remains blocked.\n");
            return 2;
        }
    } catch (...) {
        fprintf(stderr, "rAthena: runtime root rejected; startup remains blocked.\n");
        return 2;
    }
    // Preserve argv[0], every original option and the trailing null pointer.
    for (int i = index; i + 2 <= argc; ++i) argv[i] = argv[i + 2];
    argc -= 2;
    return -1; // original Core startup continues
}
} // namespace runtime_root
#endif

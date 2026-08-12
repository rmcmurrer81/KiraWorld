#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <bcrypt.h>

#include <algorithm>
#include <array>
#include <cctype>
#include <cstdint>
#include <cwctype>
#include <iostream>
#include <limits>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#pragma comment(lib, "bcrypt.lib")

namespace {

constexpr char kAuthorityId[] = "shared_growth_v9_authority_root_01";
constexpr char kTemplateSha[] = "6edad3d84a983743fa9875164e224eb52d1c3705b2670610a5abe21817dad367";
constexpr char kRoutesSha[] = "5c7ecd805c262c95dfcac2d80c7b807988215cb2418b2169d49fe7e5db3cbc3c";
constexpr char kPrivateVariantSha[] = "97946f9097dea8715ed5186e28a184e14dc6ec4eadfcb6d7b3fd03f4faa48373";
constexpr char kV8ClosureSha[] = "5a9cd887158feb056e8199bc3d03849c6d7da1b6e53c2b75be0592746c5d119e";
constexpr char kPublicKeySha[] = "a46978c9370265acb9c609fd0bfd693fb799ec899dde9fe75e9e198990e5905e";
constexpr char kAuthorConsumerSha[] = "8d8ace5367594b6543606422b8915758f750eaae8b8253f1bb90eb6aebbe600f";
constexpr char kAuthorDecisionSha[] = "aebd863133c58f03e3e2813d25940a1cb5c4e60c7776e1e879264c29c619acd9";
constexpr wchar_t kKiraRoot[] = L"C:\\Users\\robmc\\Kira";
constexpr wchar_t kAuthorLedgerParent[] =
    L"C:\\Users\\robmc\\Documents\\Codex\\2026-08-11\\c\\work\\growth_v9_author\\runtime";
constexpr wchar_t kAcceptedLedgerParent[] =
    L"C:\\Users\\robmc\\Kira\\RecoverySprint\\continuation_20260811\\shared_person_growth_v3_protected_handoff_v9_runtime";
constexpr std::uint64_t kMaxReceiptLifetimeMs = 7ULL * 24ULL * 60ULL * 60ULL * 1000ULL;
constexpr std::size_t kMaxOrdinaryFile = 2U * 1024U * 1024U;
constexpr std::size_t kMaxReceiptFile = 16U * 1024U;

class Failure final : public std::runtime_error {
 public:
  explicit Failure(const char* code) : std::runtime_error(code) {}
};

[[noreturn]] void Fail(const char* code) { throw Failure(code); }

struct Handle final {
  HANDLE value = INVALID_HANDLE_VALUE;
  Handle() = default;
  explicit Handle(HANDLE h) : value(h) {}
  Handle(const Handle&) = delete;
  Handle& operator=(const Handle&) = delete;
  Handle(Handle&& other) noexcept : value(other.value) { other.value = INVALID_HANDLE_VALUE; }
  Handle& operator=(Handle&& other) noexcept {
    if (this != &other) {
      if (value != INVALID_HANDLE_VALUE) CloseHandle(value);
      value = other.value;
      other.value = INVALID_HANDLE_VALUE;
    }
    return *this;
  }
  ~Handle() {
    if (value != INVALID_HANDLE_VALUE) CloseHandle(value);
  }
};

struct AlgHandle final {
  BCRYPT_ALG_HANDLE value = nullptr;
  ~AlgHandle() {
    if (value != nullptr) BCryptCloseAlgorithmProvider(value, 0);
  }
};

struct HashHandle final {
  BCRYPT_HASH_HANDLE value = nullptr;
  ~HashHandle() {
    if (value != nullptr) BCryptDestroyHash(value);
  }
};

struct KeyHandle final {
  BCRYPT_KEY_HANDLE value = nullptr;
  ~KeyHandle() {
    if (value != nullptr) BCryptDestroyKey(value);
  }
};

bool NtOk(NTSTATUS status) { return status >= 0; }

std::string Hex(const std::uint8_t* bytes, std::size_t count) {
  static constexpr char table[] = "0123456789abcdef";
  std::string out;
  out.resize(count * 2U);
  for (std::size_t i = 0; i < count; ++i) {
    out[i * 2U] = table[(bytes[i] >> 4U) & 0x0fU];
    out[i * 2U + 1U] = table[bytes[i] & 0x0fU];
  }
  return out;
}

int HexNibble(char ch) {
  if (ch >= '0' && ch <= '9') return ch - '0';
  if (ch >= 'a' && ch <= 'f') return 10 + ch - 'a';
  return -1;
}

std::vector<std::uint8_t> Unhex(const std::string& text, std::size_t expected_bytes) {
  if (text.size() != expected_bytes * 2U) Fail("E_HEX_LENGTH");
  std::vector<std::uint8_t> out(expected_bytes);
  for (std::size_t i = 0; i < expected_bytes; ++i) {
    const int high = HexNibble(text[i * 2U]);
    const int low = HexNibble(text[i * 2U + 1U]);
    if (high < 0 || low < 0) Fail("E_HEX_FORMAT");
    out[i] = static_cast<std::uint8_t>((high << 4) | low);
  }
  return out;
}

std::array<std::uint8_t, 32> Sha256Bytes(const std::uint8_t* data, std::size_t size) {
  if (size > static_cast<std::size_t>(std::numeric_limits<ULONG>::max())) Fail("E_HASH_SIZE");
  AlgHandle algorithm;
  if (!NtOk(BCryptOpenAlgorithmProvider(&algorithm.value, BCRYPT_SHA256_ALGORITHM, nullptr, 0))) {
    Fail("E_HASH_PROVIDER");
  }
  HashHandle hash;
  if (!NtOk(BCryptCreateHash(algorithm.value, &hash.value, nullptr, 0, nullptr, 0, 0))) {
    Fail("E_HASH_CREATE");
  }
  if (size != 0U &&
      !NtOk(BCryptHashData(hash.value, const_cast<PUCHAR>(data), static_cast<ULONG>(size), 0))) {
    Fail("E_HASH_DATA");
  }
  std::array<std::uint8_t, 32> result{};
  if (!NtOk(BCryptFinishHash(hash.value, result.data(), static_cast<ULONG>(result.size()), 0))) {
    Fail("E_HASH_FINISH");
  }
  return result;
}

std::string Sha256(const std::vector<std::uint8_t>& data) {
  const auto digest = Sha256Bytes(data.data(), data.size());
  return Hex(digest.data(), digest.size());
}

std::string Sha256(const std::string& data) {
  const auto* bytes = reinterpret_cast<const std::uint8_t*>(data.data());
  const auto digest = Sha256Bytes(bytes, data.size());
  return Hex(digest.data(), digest.size());
}

std::wstring FullPath(const std::wstring& input) {
  const DWORD needed = GetFullPathNameW(input.c_str(), 0, nullptr, nullptr);
  if (needed == 0U || needed > 32767U) Fail("E_PATH_FULL");
  std::vector<wchar_t> buffer(static_cast<std::size_t>(needed) + 1U);
  const DWORD written = GetFullPathNameW(input.c_str(), static_cast<DWORD>(buffer.size()), buffer.data(), nullptr);
  if (written == 0U || written >= buffer.size()) Fail("E_PATH_FULL");
  std::wstring result(buffer.data(), written);
  std::replace(result.begin(), result.end(), L'/', L'\\');
  while (result.size() > 3U && result.back() == L'\\') result.pop_back();
  return result;
}

std::wstring LowerPath(std::wstring path) {
  for (wchar_t& ch : path) ch = static_cast<wchar_t>(std::towlower(ch));
  return path;
}

std::string Utf8(const std::wstring& input) {
  if (input.empty()) return {};
  const int needed = WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, input.data(),
                                         static_cast<int>(input.size()), nullptr, 0, nullptr, nullptr);
  if (needed <= 0) Fail("E_PATH_UTF8");
  std::string output(static_cast<std::size_t>(needed), '\0');
  if (WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, input.data(),
                          static_cast<int>(input.size()), output.data(), needed, nullptr, nullptr) != needed) {
    Fail("E_PATH_UTF8");
  }
  return output;
}

bool PathUnder(const std::wstring& path, const std::wstring& parent) {
  const std::wstring low_path = LowerPath(FullPath(path));
  const std::wstring low_parent = LowerPath(FullPath(parent));
  return low_path.size() > low_parent.size() &&
         low_path.compare(0, low_parent.size(), low_parent) == 0 &&
         low_path[low_parent.size()] == L'\\' &&
         low_path.find(L'\\', low_parent.size() + 1U) == std::wstring::npos;
}

void CheckExistingPathComponentsNoReparse(const std::wstring& input, bool final_may_be_missing) {
  const std::wstring path = FullPath(input);
  if (path.size() < 3U || path[1] != L':' || path[2] != L'\\') Fail("E_PATH_ROOT");
  std::wstring current = path.substr(0, 3U);
  std::size_t position = 3U;
  while (position < path.size()) {
    const std::size_t next = path.find(L'\\', position);
    const bool final = next == std::wstring::npos;
    const std::wstring part = path.substr(position, final ? std::wstring::npos : next - position);
    if (part.empty() || part == L"." || part == L"..") Fail("E_PATH_COMPONENT");
    if (current.back() != L'\\') current.push_back(L'\\');
    current.append(part);
    const DWORD attrs = GetFileAttributesW(current.c_str());
    if (attrs == INVALID_FILE_ATTRIBUTES) {
      if (final && final_may_be_missing && GetLastError() == ERROR_FILE_NOT_FOUND) return;
      Fail("E_PATH_MISSING");
    }
    if ((attrs & FILE_ATTRIBUTE_REPARSE_POINT) != 0U) Fail("E_PATH_REPARSE");
    if (!final && (attrs & FILE_ATTRIBUTE_DIRECTORY) == 0U) Fail("E_PATH_COMPONENT_TYPE");
    if (final) return;
    position = next + 1U;
  }
}

std::vector<std::uint8_t> ReadFileExact(const std::wstring& input, std::size_t maximum) {
  const std::wstring path = FullPath(input);
  CheckExistingPathComponentsNoReparse(path, false);
  Handle handle(CreateFileW(path.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING,
                            FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OPEN_REPARSE_POINT | FILE_FLAG_SEQUENTIAL_SCAN,
                            nullptr));
  if (handle.value == INVALID_HANDLE_VALUE) Fail("E_FILE_OPEN");
  BY_HANDLE_FILE_INFORMATION info{};
  if (!GetFileInformationByHandle(handle.value, &info)) Fail("E_FILE_INFO");
  if ((info.dwFileAttributes & (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT)) != 0U) {
    Fail("E_FILE_TYPE");
  }
  const ULONGLONG size64 = (static_cast<ULONGLONG>(info.nFileSizeHigh) << 32U) | info.nFileSizeLow;
  if (size64 > maximum) Fail("E_FILE_SIZE");
  const std::size_t size = static_cast<std::size_t>(size64);
  std::vector<std::uint8_t> data(size);
  std::size_t offset = 0U;
  while (offset < size) {
    const DWORD request = static_cast<DWORD>(std::min<std::size_t>(size - offset, 1U << 20U));
    DWORD received = 0U;
    if (!ReadFile(handle.value, data.data() + offset, request, &received, nullptr) || received == 0U) {
      Fail("E_FILE_READ");
    }
    offset += received;
  }
  return data;
}

bool IsSafeAsciiValue(const std::string& value) {
  if (value.empty() || value.size() > 2048U) return false;
  for (const unsigned char ch : value) {
    if (ch < 0x21U || ch > 0x7eU || ch == '=') return false;
  }
  return true;
}

std::vector<std::string> SplitExact(const std::string& text, char delimiter) {
  std::vector<std::string> result;
  std::size_t start = 0U;
  while (true) {
    const std::size_t position = text.find(delimiter, start);
    if (position == std::string::npos) {
      result.emplace_back(text.substr(start));
      return result;
    }
    result.emplace_back(text.substr(start, position - start));
    start = position + 1U;
  }
}

std::vector<std::string> StrictLines(const std::vector<std::uint8_t>& data) {
  if (data.empty() || data.back() != static_cast<std::uint8_t>('\n')) Fail("E_TEXT_FINAL_LF");
  std::string text;
  text.reserve(data.size());
  for (const std::uint8_t byte : data) {
    if (byte == 0U || byte == static_cast<std::uint8_t>('\r') ||
        (byte != static_cast<std::uint8_t>('\n') && (byte < 0x20U || byte > 0x7eU) && byte != 0x09U)) {
      Fail("E_TEXT_ENCODING");
    }
    text.push_back(static_cast<char>(byte));
  }
  std::vector<std::string> lines = SplitExact(text, '\n');
  if (lines.empty() || !lines.back().empty()) Fail("E_TEXT_FINAL_LF");
  lines.pop_back();
  for (const std::string& line : lines) {
    if (line.empty()) Fail("E_TEXT_EMPTY_LINE");
  }
  return lines;
}

std::uint64_t ParseUnsigned(const std::string& text) {
  if (text.empty() || (text.size() > 1U && text.front() == '0')) Fail("E_INTEGER_FORMAT");
  std::uint64_t value = 0U;
  for (const char ch : text) {
    if (ch < '0' || ch > '9') Fail("E_INTEGER_FORMAT");
    const std::uint64_t digit = static_cast<std::uint64_t>(ch - '0');
    if (value > (std::numeric_limits<std::uint64_t>::max() - digit) / 10U) Fail("E_INTEGER_RANGE");
    value = value * 10U + digit;
  }
  return value;
}

void RequireHash(const std::vector<std::uint8_t>& data, const char* expected, const char* error) {
  if (Sha256(data) != expected) Fail(error);
}

struct Receipt {
  std::map<std::string, std::string> fields;
  std::string body;
  std::vector<std::uint8_t> signature;
  std::string complete_sha;
};

const std::array<const char*, 40> kReceiptOrder = {
    "schema", "receipt_id", "authority_id", "authority_epoch", "sequence", "issued_unix_ms",
    "expires_unix_ms", "authorization_mode", "target_kind", "recipient_id", "route_id",
    "candidate_id", "person_class", "maturity_status", "maturity_source_id", "creation_class",
    "variant_entry_id", "scope", "recipient_opt_in", "revocable", "owner_override_allowed",
    "private_state_requested", "memory_write_requested", "external_action_requested",
    "consumer_entrypoint_id", "native_engine_sha256", "consumer_artifact_sha256",
    "independent_audit_decision_sha256",
    "template_sha256", "route_descriptor_sha256", "private_variant_control_sha256",
    "v8_closure_descriptor_sha256", "ledger_id", "ledger_root_path_sha256",
    "expected_ledger_revision", "expected_prior_head_sha256", "nonce_hex", "single_use",
    "production_enabled", "different_reviewer_required"};

Receipt ParseReceipt(const std::vector<std::uint8_t>& data) {
  const std::vector<std::string> lines = StrictLines(data);
  if (lines.size() != kReceiptOrder.size() + 1U) Fail("E_RECEIPT_FIELD_COUNT");
  Receipt result;
  for (std::size_t i = 0; i < kReceiptOrder.size(); ++i) {
    const std::string prefix = std::string(kReceiptOrder[i]) + "=";
    if (lines[i].compare(0, prefix.size(), prefix) != 0) Fail("E_RECEIPT_ORDER");
    const std::string value = lines[i].substr(prefix.size());
    if (!IsSafeAsciiValue(value)) Fail("E_RECEIPT_VALUE");
    result.fields.emplace(kReceiptOrder[i], value);
    result.body.append(lines[i]).push_back('\n');
  }
  const std::string signature_prefix = "signature_hex=";
  if (lines.back().compare(0, signature_prefix.size(), signature_prefix) != 0) {
    Fail("E_RECEIPT_SIGNATURE_FIELD");
  }
  result.signature = Unhex(lines.back().substr(signature_prefix.size()), 64U);
  result.complete_sha = Sha256(data);
  return result;
}

const std::string& Field(const Receipt& receipt, const char* name) {
  const auto found = receipt.fields.find(name);
  if (found == receipt.fields.end()) Fail("E_RECEIPT_MISSING");
  return found->second;
}

void VerifySignature(const Receipt& receipt, const std::vector<std::uint8_t>& raw_public) {
  if (raw_public.size() != 64U) Fail("E_PUBLIC_KEY_SIZE");
  AlgHandle algorithm;
  if (!NtOk(BCryptOpenAlgorithmProvider(&algorithm.value, BCRYPT_ECDSA_P256_ALGORITHM, nullptr, 0))) {
    Fail("E_SIGNATURE_PROVIDER");
  }
  BCRYPT_ECCKEY_BLOB header{};
  header.dwMagic = BCRYPT_ECDSA_PUBLIC_P256_MAGIC;
  header.cbKey = 32U;
  std::vector<std::uint8_t> blob(sizeof(header) + raw_public.size());
  std::copy_n(reinterpret_cast<const std::uint8_t*>(&header), sizeof(header), blob.begin());
  std::copy(raw_public.begin(), raw_public.end(), blob.begin() + static_cast<std::ptrdiff_t>(sizeof(header)));
  KeyHandle key;
  if (!NtOk(BCryptImportKeyPair(algorithm.value, nullptr, BCRYPT_ECCPUBLIC_BLOB, &key.value,
                                blob.data(), static_cast<ULONG>(blob.size()), 0))) {
    Fail("E_PUBLIC_KEY_IMPORT");
  }
  const auto digest = Sha256Bytes(reinterpret_cast<const std::uint8_t*>(receipt.body.data()),
                                 receipt.body.size());
  if (!NtOk(BCryptVerifySignature(key.value, nullptr, const_cast<PUCHAR>(digest.data()),
                                  static_cast<ULONG>(digest.size()),
                                  const_cast<PUCHAR>(receipt.signature.data()),
                                  static_cast<ULONG>(receipt.signature.size()), 0))) {
    Fail("E_SIGNATURE_INVALID");
  }
}

std::uint64_t NowUnixMs() {
  FILETIME time{};
  GetSystemTimeAsFileTime(&time);
  ULARGE_INTEGER value{};
  value.LowPart = time.dwLowDateTime;
  value.HighPart = time.dwHighDateTime;
  constexpr std::uint64_t epoch_delta = 116444736000000000ULL;
  if (value.QuadPart < epoch_delta) Fail("E_CLOCK");
  return (value.QuadPart - epoch_delta) / 10000ULL;
}

struct Route {
  std::string route_id;
  std::string recipient_id;
  std::string candidate_id;
  std::string person_class;
  std::string maturity_status;
  std::string maturity_source_id;
  std::string disposition;
};

std::map<std::string, Route> ParseRoutes(const std::vector<std::uint8_t>& data) {
  const std::vector<std::string> lines = StrictLines(data);
  if (lines.size() != 38U) Fail("E_ROUTE_COUNT");
  std::map<std::string, Route> routes;
  for (const std::string& line : lines) {
    const auto parts = SplitExact(line, '\t');
    if (parts.size() != 7U) Fail("E_ROUTE_COLUMNS");
    for (const auto& part : parts) if (!IsSafeAsciiValue(part)) Fail("E_ROUTE_VALUE");
    Route route{parts[0], parts[1], parts[2], parts[3], parts[4], parts[5], parts[6]};
    if (!routes.emplace(route.route_id, route).second) Fail("E_ROUTE_DUPLICATE");
  }
  return routes;
}

struct VariantPrivate {
  std::string entry_id;
  std::string source_kind;
  std::string source_id;
  std::string public_record;
  std::string selected_continuity;
  std::string selected_source_version;
  std::string selection_basis;
  std::string public_projection_set;
};

std::map<std::string, VariantPrivate> ParsePrivateVariants(const std::vector<std::uint8_t>& data) {
  const std::vector<std::string> lines = StrictLines(data);
  if (lines.size() != 2U) Fail("E_VARIANT_COUNT");
  std::map<std::string, VariantPrivate> variants;
  for (const std::string& line : lines) {
    const auto parts = SplitExact(line, '\t');
    if (parts.size() != 23U) Fail("E_VARIANT_COLUMNS");
    for (const auto& part : parts) if (!IsSafeAsciiValue(part)) Fail("E_VARIANT_VALUE");
    const std::uint64_t branch_ordinal = ParseUnsigned(parts[11]);
    const std::uint64_t fatal_ordinal = ParseUnsigned(parts[12]);
    if (branch_ordinal >= fatal_ordinal || parts[13] != "true" || parts[14] != "true" ||
        parts[15] != "false" || parts[16] != "false" || parts[17] != "true" ||
        parts[18] != "false" || parts[19] != "true" || parts[20] != "true" ||
        parts[21] != "true" || parts[22] != "true") {
      Fail("E_VARIANT_PRIVATE_POLICY");
    }
    if (parts[1] != "fictional_source" && parts[1] != "historical_source") {
      Fail("E_VARIANT_SOURCE_KIND");
    }
    VariantPrivate value{parts[0], parts[1], parts[2], parts[3], parts[4], parts[5], parts[6], parts[7]};
    if (!variants.emplace(value.entry_id, value).second) Fail("E_VARIANT_DUPLICATE");
  }
  return variants;
}

void VerifyV8Closure(const std::vector<std::uint8_t>& descriptor) {
  const auto lines = StrictLines(descriptor);
  if (lines.size() != 11U) Fail("E_V8_CLOSURE_COUNT");
  std::set<std::string> seen;
  for (const std::string& line : lines) {
    const auto parts = SplitExact(line, '\t');
    if (parts.size() != 4U || parts[0].empty() || parts[0].front() == '/' ||
        parts[0].find("..") != std::string::npos || parts[0].find(':') != std::string::npos ||
        parts[2].size() != 64U || Unhex(parts[2], 32U).size() != 32U) {
      Fail("E_V8_CLOSURE_ROW");
    }
    if (!seen.insert(parts[0]).second) Fail("E_V8_CLOSURE_DUPLICATE");
    std::wstring relative;
    relative.reserve(parts[0].size());
    for (const char ch : parts[0]) relative.push_back(ch == '/' ? L'\\' : static_cast<wchar_t>(ch));
    const std::wstring path = std::wstring(kKiraRoot) + L"\\" + relative;
    const auto contents = ReadFileExact(path, kMaxOrdinaryFile);
    if (contents.size() != ParseUnsigned(parts[1]) || Sha256(contents) != parts[2]) {
      Fail("E_V8_CLOSURE_DRIFT");
    }
  }
}

std::string Genesis(const std::string& ledger_id, std::uint64_t epoch) {
  std::ostringstream body;
  body << "schema=kira.shared_growth_v9.ledger_genesis.v1\n"
       << "authority_id=" << kAuthorityId << "\n"
       << "ledger_id=" << ledger_id << "\n"
       << "authority_epoch=" << epoch << "\n";
  return Sha256(body.str());
}

std::string RecordHead(const Receipt& receipt) {
  const std::uint64_t revision = ParseUnsigned(Field(receipt, "expected_ledger_revision")) + 1U;
  std::ostringstream body;
  body << "schema=kira.shared_growth_v9.ledger_record.v1\n"
       << "authority_epoch=" << Field(receipt, "authority_epoch") << "\n"
       << "revision=" << revision << "\n"
       << "receipt_id=" << Field(receipt, "receipt_id") << "\n"
       << "receipt_sha256=" << receipt.complete_sha << "\n"
       << "nonce_hex=" << Field(receipt, "nonce_hex") << "\n"
       << "native_engine_sha256=" << Field(receipt, "native_engine_sha256") << "\n"
       << "consumer_artifact_sha256=" << Field(receipt, "consumer_artifact_sha256") << "\n"
       << "target_kind=" << Field(receipt, "target_kind") << "\n"
       << "recipient_id=" << Field(receipt, "recipient_id") << "\n"
       << "route_id=" << Field(receipt, "route_id") << "\n"
       << "template_sha256=" << Field(receipt, "template_sha256") << "\n"
       << "prior_head_sha256=" << Field(receipt, "expected_prior_head_sha256") << "\n";
  return Sha256(body.str());
}

struct Record {
  std::string receipt_id;
  std::string receipt_sha;
  std::string nonce;
};

struct Ledger {
  std::string ledger_id;
  std::uint64_t epoch = 1U;
  std::uint64_t revision = 0U;
  std::string head;
  std::vector<Record> records;
};

std::string SerializeLedger(const Ledger& ledger) {
  std::ostringstream out;
  out << "schema=kira.shared_growth_v9.ledger.v1\n"
      << "authority_id=" << kAuthorityId << "\n"
      << "ledger_id=" << ledger.ledger_id << "\n"
      << "authority_epoch=" << ledger.epoch << "\n"
      << "revision=" << ledger.revision << "\n"
      << "head_sha256=" << ledger.head << "\n"
      << "record_count=" << ledger.records.size() << "\n";
  for (std::size_t i = 0; i < ledger.records.size(); ++i) {
    const std::size_t n = i + 1U;
    out << "record." << n << ".receipt_id=" << ledger.records[i].receipt_id << "\n"
        << "record." << n << ".receipt_sha256=" << ledger.records[i].receipt_sha << "\n"
        << "record." << n << ".nonce_hex=" << ledger.records[i].nonce << "\n";
  }
  return out.str();
}

std::map<std::string, std::string> ParseKeyValueLines(const std::vector<std::uint8_t>& data) {
  const auto lines = StrictLines(data);
  std::map<std::string, std::string> result;
  for (const auto& line : lines) {
    const std::size_t split = line.find('=');
    if (split == std::string::npos || split == 0U || split + 1U == line.size()) Fail("E_STATE_ROW");
    const std::string key = line.substr(0, split);
    const std::string value = line.substr(split + 1U);
    if (!IsSafeAsciiValue(key) || !IsSafeAsciiValue(value) || !result.emplace(key, value).second) {
      Fail("E_STATE_ROW");
    }
  }
  return result;
}

const std::string& MapValue(const std::map<std::string, std::string>& values, const std::string& key) {
  const auto found = values.find(key);
  if (found == values.end()) Fail("E_STATE_MISSING");
  return found->second;
}

Ledger ParseLedger(const std::vector<std::uint8_t>& data) {
  const auto values = ParseKeyValueLines(data);
  if (MapValue(values, "schema") != "kira.shared_growth_v9.ledger.v1" ||
      MapValue(values, "authority_id") != kAuthorityId) Fail("E_LEDGER_HEADER");
  Ledger result;
  result.ledger_id = MapValue(values, "ledger_id");
  result.epoch = ParseUnsigned(MapValue(values, "authority_epoch"));
  result.revision = ParseUnsigned(MapValue(values, "revision"));
  result.head = MapValue(values, "head_sha256");
  Unhex(result.head, 32U);
  const std::uint64_t count = ParseUnsigned(MapValue(values, "record_count"));
  if (count != result.revision || count > 100000U ||
      values.size() != static_cast<std::size_t>(7U + count * 3U)) Fail("E_LEDGER_COUNT");
  for (std::uint64_t i = 1U; i <= count; ++i) {
    const std::string prefix = "record." + std::to_string(i);
    Record record{MapValue(values, prefix + ".receipt_id"),
                  MapValue(values, prefix + ".receipt_sha256"),
                  MapValue(values, prefix + ".nonce_hex")};
    Unhex(record.receipt_sha, 32U);
    Unhex(record.nonce, 32U);
    result.records.push_back(std::move(record));
  }
  return result;
}

std::string SerializeAnchor(const Ledger& ledger, const std::string& ledger_sha) {
  std::ostringstream out;
  out << "schema=kira.shared_growth_v9.native_anchor.v1\n"
      << "authority_id=" << kAuthorityId << "\n"
      << "ledger_id=" << ledger.ledger_id << "\n"
      << "authority_epoch=" << ledger.epoch << "\n"
      << "revision=" << ledger.revision << "\n"
      << "head_sha256=" << ledger.head << "\n"
      << "ledger_sha256=" << ledger_sha << "\n";
  return out.str();
}

void VerifyAnchor(const std::vector<std::uint8_t>& anchor_data, const Ledger& ledger,
                  const std::vector<std::uint8_t>& ledger_data) {
  const auto values = ParseKeyValueLines(anchor_data);
  if (values.size() != 7U || MapValue(values, "schema") != "kira.shared_growth_v9.native_anchor.v1" ||
      MapValue(values, "authority_id") != kAuthorityId ||
      MapValue(values, "ledger_id") != ledger.ledger_id ||
      ParseUnsigned(MapValue(values, "authority_epoch")) != ledger.epoch ||
      ParseUnsigned(MapValue(values, "revision")) != ledger.revision ||
      MapValue(values, "head_sha256") != ledger.head ||
      MapValue(values, "ledger_sha256") != Sha256(ledger_data)) {
    Fail("E_ANCHOR_MISMATCH");
  }
}

bool Exists(const std::wstring& path) {
  const DWORD attributes = GetFileAttributesW(path.c_str());
  if (attributes == INVALID_FILE_ATTRIBUTES) {
    const DWORD error = GetLastError();
    if (error == ERROR_FILE_NOT_FOUND || error == ERROR_PATH_NOT_FOUND) return false;
    Fail("E_STATE_ATTRIBUTES");
  }
  if ((attributes & (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT)) != 0U) {
    Fail("E_STATE_TYPE");
  }
  return true;
}

void WriteNewDebt(const std::wstring& path, const std::string& data) {
  Handle file(CreateFileW(path.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_NEW,
                          FILE_ATTRIBUTE_HIDDEN | FILE_FLAG_WRITE_THROUGH, nullptr));
  if (file.value == INVALID_HANDLE_VALUE) Fail("E_DEBT_CREATE");
  DWORD written = 0U;
  if (!WriteFile(file.value, data.data(), static_cast<DWORD>(data.size()), &written, nullptr) ||
      written != data.size() || !FlushFileBuffers(file.value)) Fail("E_DEBT_WRITE");
}

void AtomicReplace(const std::wstring& path, const std::string& data, const wchar_t* suffix) {
  const std::wstring temp = path + suffix;
  if (Exists(temp)) Fail("E_TEMP_EXISTS");
  Handle file(CreateFileW(temp.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_NEW,
                          FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH, nullptr));
  if (file.value == INVALID_HANDLE_VALUE) Fail("E_TEMP_CREATE");
  DWORD written = 0U;
  if (!WriteFile(file.value, data.data(), static_cast<DWORD>(data.size()), &written, nullptr) ||
      written != data.size() || !FlushFileBuffers(file.value)) Fail("E_TEMP_WRITE");
  file = Handle();
  if (!MoveFileExW(temp.c_str(), path.c_str(), MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)) {
    Fail("E_STATE_REPLACE");
  }
}

std::string JsonEscape(const std::string& input) {
  std::string result;
  for (const unsigned char ch : input) {
    if (ch == '"' || ch == '\\') {
      result.push_back('\\');
      result.push_back(static_cast<char>(ch));
    } else if (ch >= 0x20U && ch <= 0x7eU) {
      result.push_back(static_cast<char>(ch));
    } else {
      Fail("E_JSON_VALUE");
    }
  }
  return result;
}

std::map<std::wstring, std::wstring> ParseArguments(int argc, wchar_t** argv) {
  if (argc != 19) Fail("E_ARGUMENT_COUNT");
  const std::set<std::wstring> allowed = {L"--receipt", L"--ledger-root", L"--template", L"--routes",
                                          L"--private-variant", L"--v8-closure", L"--public-key",
                                          L"--consumer", L"--audit-decision"};
  std::map<std::wstring, std::wstring> result;
  for (int i = 1; i < argc; i += 2) {
    const std::wstring key(argv[i]);
    if (allowed.count(key) != 1U || argv[i + 1][0] == L'\0' ||
        !result.emplace(key, argv[i + 1]).second) Fail("E_ARGUMENTS");
  }
  if (result.size() != allowed.size()) Fail("E_ARGUMENTS");
  return result;
}

std::vector<std::uint8_t> ReadCurrentModule() {
  std::vector<wchar_t> buffer(32768U);
  const DWORD written = GetModuleFileNameW(nullptr, buffer.data(), static_cast<DWORD>(buffer.size()));
  if (written == 0U || written >= buffer.size()) Fail("E_ENGINE_PATH");
  return ReadFileExact(std::wstring(buffer.data(), written), 16U * 1024U * 1024U);
}

void RequireBoolean(const Receipt& receipt, const char* key, const char* expected) {
  if (Field(receipt, key) != expected) Fail("E_RECEIPT_POLICY");
}

void ValidateReceiptPolicy(const Receipt& receipt, const Route& route,
                           const std::wstring& ledger_root,
                           const std::string& native_engine_sha,
                           const std::vector<std::uint8_t>& consumer,
                           const std::vector<std::uint8_t>& decision) {
  if (Field(receipt, "schema") != "kira.shared_growth_v9.authority_receipt.v1" ||
      Field(receipt, "authority_id") != kAuthorityId || Field(receipt, "authority_epoch") != "1") {
    Fail("E_RECEIPT_AUTHORITY");
  }
  if (Field(receipt, "template_sha256") != kTemplateSha ||
      Field(receipt, "route_descriptor_sha256") != kRoutesSha ||
      Field(receipt, "private_variant_control_sha256") != kPrivateVariantSha ||
      Field(receipt, "v8_closure_descriptor_sha256") != kV8ClosureSha ||
      Field(receipt, "scope") != "shared_growth_v9_public_general_template_handoff") {
    Fail("E_RECEIPT_SCOPE");
  }
  RequireBoolean(receipt, "recipient_opt_in", "true");
  RequireBoolean(receipt, "revocable", "true");
  RequireBoolean(receipt, "owner_override_allowed", "false");
  RequireBoolean(receipt, "private_state_requested", "false");
  RequireBoolean(receipt, "memory_write_requested", "false");
  RequireBoolean(receipt, "external_action_requested", "false");
  RequireBoolean(receipt, "single_use", "true");
  RequireBoolean(receipt, "production_enabled", "false");
  RequireBoolean(receipt, "different_reviewer_required", "true");
  if (Field(receipt, "native_engine_sha256") != native_engine_sha ||
      Field(receipt, "consumer_artifact_sha256") != Sha256(consumer) ||
      Field(receipt, "independent_audit_decision_sha256") != Sha256(decision)) {
    Fail("E_RECEIPT_CONSUMER_BINDING");
  }
  const std::string& mode = Field(receipt, "authorization_mode");
  if (mode == "author_test") {
    if (Field(receipt, "consumer_entrypoint_id") != "author_test_harness_v1" ||
        Field(receipt, "consumer_artifact_sha256") != kAuthorConsumerSha ||
        Field(receipt, "independent_audit_decision_sha256") != kAuthorDecisionSha ||
        !PathUnder(ledger_root, kAuthorLedgerParent)) Fail("E_AUTHOR_TEST_BOUNDARY");
  } else if (mode == "independent_acceptance") {
    if (Field(receipt, "consumer_entrypoint_id") != "shared_growth_v9_receiver_adapter_v1" ||
        Field(receipt, "consumer_artifact_sha256") == kAuthorConsumerSha ||
        Field(receipt, "independent_audit_decision_sha256") == kAuthorDecisionSha ||
        !PathUnder(ledger_root, kAcceptedLedgerParent)) Fail("E_ACCEPTANCE_BOUNDARY");
  } else {
    Fail("E_AUTHORIZATION_MODE");
  }
  const std::wstring canonical = LowerPath(FullPath(ledger_root));
  if (Field(receipt, "ledger_root_path_sha256") != Sha256(Utf8(canonical))) {
    Fail("E_LEDGER_PATH_BINDING");
  }
  const std::uint64_t issued = ParseUnsigned(Field(receipt, "issued_unix_ms"));
  const std::uint64_t expires = ParseUnsigned(Field(receipt, "expires_unix_ms"));
  const std::uint64_t now = NowUnixMs();
  if (expires <= issued || expires - issued > kMaxReceiptLifetimeMs || issued > now || now >= expires) {
    Fail("E_RECEIPT_TIME");
  }
  const std::uint64_t sequence = ParseUnsigned(Field(receipt, "sequence"));
  const std::uint64_t expected_revision = ParseUnsigned(Field(receipt, "expected_ledger_revision"));
  if (sequence == 0U || expected_revision == std::numeric_limits<std::uint64_t>::max() ||
      sequence != expected_revision + 1U) Fail("E_RECEIPT_SEQUENCE");
  Unhex(Field(receipt, "expected_prior_head_sha256"), 32U);
  Unhex(Field(receipt, "nonce_hex"), 32U);
  if (route.disposition == "frozen_no_handoff") Fail("E_FROZEN_ROUTE");
  if (route.disposition != (Field(receipt, "target_kind") == "temporary_creator"
                                ? "applicable_creator_template"
                                : "applicable_existing_person")) Fail("E_ROUTE_DISPOSITION");
  if (Field(receipt, "recipient_id") != route.recipient_id ||
      Field(receipt, "candidate_id") != route.candidate_id ||
      Field(receipt, "person_class") != route.person_class ||
      Field(receipt, "maturity_status") != route.maturity_status ||
      Field(receipt, "maturity_source_id") != route.maturity_source_id) Fail("E_ROUTE_BINDING");
}

std::string BuildOutput(const Receipt& receipt, const Route& route, const Ledger& ledger,
                        const VariantPrivate* variant) {
  std::ostringstream out;
  out << "{"
      << "\"schema\":\"kira.shared_growth_v9.handoff_proposal.v1\","
      << "\"status\":\"HANDOFF_PROPOSAL_ONLY\","
      << "\"authorization_mode\":\"" << JsonEscape(Field(receipt, "authorization_mode")) << "\","
      << "\"target_kind\":\"" << JsonEscape(Field(receipt, "target_kind")) << "\","
      << "\"recipient_id\":\"" << JsonEscape(route.recipient_id) << "\","
      << "\"route_id\":\"" << JsonEscape(route.route_id) << "\","
      << "\"candidate_id\":\"" << JsonEscape(route.candidate_id) << "\","
      << "\"person_class\":\"" << JsonEscape(route.person_class) << "\","
      << "\"maturity_status\":\"" << JsonEscape(route.maturity_status) << "\","
      << "\"maturity_source_id\":\"" << JsonEscape(route.maturity_source_id) << "\","
      << "\"public_template_sha256\":\"" << kTemplateSha << "\","
      << "\"native_engine_sha256\":\"" << JsonEscape(Field(receipt, "native_engine_sha256")) << "\","
      << "\"ledger_revision\":" << ledger.revision << ","
      << "\"ledger_head_sha256\":\"" << ledger.head << "\","
      << "\"recipient_opt_in\":true,"
      << "\"revocable\":true,"
      << "\"owner_override_allowed\":false,"
      << "\"private_state_requested\":false,"
      << "\"memory_write_requested\":false,"
      << "\"external_action_requested\":false,"
      << "\"person_changed\":false,"
      << "\"temporary_creator_changed\":false,"
      << "\"production_enabled\":false,"
      << "\"requires_receiver_integration_audit\":true";
  if (variant != nullptr) {
    out << ",\"variant_public_projection\":{"
        << "\"source_kind\":\"" << JsonEscape(variant->source_kind) << "\","
        << "\"source_id\":\"" << JsonEscape(variant->source_id) << "\","
        << "\"public_record\":\"" << JsonEscape(variant->public_record) << "\","
        << "\"selected_continuity\":\"" << JsonEscape(variant->selected_continuity) << "\","
        << "\"selected_source_version\":\"" << JsonEscape(variant->selected_source_version) << "\","
        << "\"selection_basis\":\"" << JsonEscape(variant->selection_basis) << "\","
        << "\"public_projection_set\":\"" << JsonEscape(variant->public_projection_set) << "\","
        << "\"source_alive_at_selection\":true,"
        << "\"exact_subjective_memory_claimed\":false,"
        << "\"selected_history_stops_at_source_version\":true,"
        << "\"post_selection_memory_history_is_new\":true}";
  }
  out << "}\n";
  return out.str();
}

void Run(int argc, wchar_t** argv) {
  const auto arguments = ParseArguments(argc, argv);
  const std::string native_engine_sha = Sha256(ReadCurrentModule());
  const auto receipt_bytes = ReadFileExact(arguments.at(L"--receipt"), kMaxReceiptFile);
  const auto template_bytes = ReadFileExact(arguments.at(L"--template"), kMaxOrdinaryFile);
  const auto routes_bytes = ReadFileExact(arguments.at(L"--routes"), kMaxOrdinaryFile);
  const auto variant_bytes = ReadFileExact(arguments.at(L"--private-variant"), kMaxOrdinaryFile);
  const auto closure_bytes = ReadFileExact(arguments.at(L"--v8-closure"), kMaxOrdinaryFile);
  const auto key_bytes = ReadFileExact(arguments.at(L"--public-key"), 64U);
  const auto consumer_bytes = ReadFileExact(arguments.at(L"--consumer"), kMaxOrdinaryFile);
  const auto decision_bytes = ReadFileExact(arguments.at(L"--audit-decision"), kMaxOrdinaryFile);
  RequireHash(template_bytes, kTemplateSha, "E_TEMPLATE_DRIFT");
  RequireHash(routes_bytes, kRoutesSha, "E_ROUTES_DRIFT");
  RequireHash(variant_bytes, kPrivateVariantSha, "E_VARIANT_DRIFT");
  RequireHash(closure_bytes, kV8ClosureSha, "E_V8_DESCRIPTOR_DRIFT");
  RequireHash(key_bytes, kPublicKeySha, "E_PUBLIC_KEY_DRIFT");
  VerifyV8Closure(closure_bytes);
  const auto routes = ParseRoutes(routes_bytes);
  const auto variants = ParsePrivateVariants(variant_bytes);
  const Receipt receipt = ParseReceipt(receipt_bytes);
  VerifySignature(receipt, key_bytes);
  const auto route_found = routes.find(Field(receipt, "route_id"));
  if (route_found == routes.end()) Fail("E_ROUTE_NOT_FOUND");
  const Route& route = route_found->second;
  const std::wstring ledger_root = FullPath(arguments.at(L"--ledger-root"));
  ValidateReceiptPolicy(receipt, route, ledger_root, native_engine_sha, consumer_bytes, decision_bytes);

  const std::string target_kind = Field(receipt, "target_kind");
  const VariantPrivate* variant = nullptr;
  if (target_kind == "existing_person") {
    if (Field(receipt, "creation_class") != "none" || Field(receipt, "variant_entry_id") != "none") {
      Fail("E_EXISTING_PERSON_BOUNDARY");
    }
  } else if (target_kind == "temporary_creator") {
    if (route.recipient_id != "temporary_creator" || route.candidate_id != "temporary_creator") {
      Fail("E_CREATOR_BOUNDARY");
    }
    const std::string& creation = Field(receipt, "creation_class");
    const std::string expected = route.route_id == "creator:new_variant"
                                     ? "variant"
                                     : (route.route_id == "creator:new_expert" ? "expert" : "synthetic_person");
    if (creation != expected) Fail("E_CREATOR_CLASS");
    if (creation == "variant") {
      const auto found = variants.find(Field(receipt, "variant_entry_id"));
      if (found == variants.end()) Fail("E_VARIANT_NOT_FOUND");
      variant = &found->second;
    } else if (Field(receipt, "variant_entry_id") != "none") {
      Fail("E_CREATOR_VARIANT_ID");
    }
  } else {
    Fail("E_TARGET_KIND");
  }

  CheckExistingPathComponentsNoReparse(ledger_root, true);
  if (!CreateDirectoryW(ledger_root.c_str(), nullptr) && GetLastError() != ERROR_ALREADY_EXISTS) {
    Fail("E_LEDGER_DIRECTORY_CREATE");
  }
  CheckExistingPathComponentsNoReparse(ledger_root, false);
  const std::wstring lock_path = ledger_root + L"\\ledger.lock";
  Handle lock(CreateFileW(lock_path.c_str(), GENERIC_READ | GENERIC_WRITE, 0, nullptr, OPEN_ALWAYS,
                          FILE_ATTRIBUTE_HIDDEN | FILE_FLAG_OPEN_REPARSE_POINT, nullptr));
  if (lock.value == INVALID_HANDLE_VALUE) Fail("E_LEDGER_LOCK");
  BY_HANDLE_FILE_INFORMATION lock_info{};
  if (!GetFileInformationByHandle(lock.value, &lock_info) ||
      (lock_info.dwFileAttributes & (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT)) != 0U) {
    Fail("E_LEDGER_LOCK_TYPE");
  }
  const std::wstring ledger_path = ledger_root + L"\\ledger.v9";
  const std::wstring anchor_path = ledger_root + L"\\anchor.v9";
  const std::wstring debt_path = ledger_root + L"\\recovery_debt.v9";
  if (Exists(debt_path)) Fail("E_RECOVERY_DEBT");
  const bool ledger_exists = Exists(ledger_path);
  const bool anchor_exists = Exists(anchor_path);
  if (ledger_exists != anchor_exists) Fail("E_STATE_PAIR");
  Ledger ledger;
  ledger.ledger_id = Field(receipt, "ledger_id");
  ledger.epoch = 1U;
  ledger.head = Genesis(ledger.ledger_id, ledger.epoch);
  if (ledger_exists) {
    const auto ledger_data = ReadFileExact(ledger_path, kMaxOrdinaryFile);
    const auto anchor_data = ReadFileExact(anchor_path, kMaxOrdinaryFile);
    ledger = ParseLedger(ledger_data);
    VerifyAnchor(anchor_data, ledger, ledger_data);
    if (ledger.ledger_id != Field(receipt, "ledger_id") || ledger.epoch != 1U) Fail("E_LEDGER_IDENTITY");
  }
  const std::uint64_t expected_revision = ParseUnsigned(Field(receipt, "expected_ledger_revision"));
  if (ledger.revision != expected_revision || ledger.head != Field(receipt, "expected_prior_head_sha256")) {
    Fail("E_LEDGER_EXPECTATION");
  }
  for (const auto& record : ledger.records) {
    if (record.receipt_id == Field(receipt, "receipt_id") || record.nonce == Field(receipt, "nonce_hex")) {
      Fail("E_RECEIPT_REPLAY");
    }
  }
  ledger.revision += 1U;
  ledger.head = RecordHead(receipt);
  ledger.records.push_back(Record{Field(receipt, "receipt_id"), receipt.complete_sha,
                                  Field(receipt, "nonce_hex")});
  const std::string ledger_text = SerializeLedger(ledger);
  const std::string anchor_text = SerializeAnchor(ledger, Sha256(ledger_text));
  std::ostringstream debt;
  debt << "schema=kira.shared_growth_v9.recovery_debt.v1\n"
       << "ledger_id=" << ledger.ledger_id << "\n"
       << "pending_revision=" << ledger.revision << "\n"
       << "pending_head_sha256=" << ledger.head << "\n";
  WriteNewDebt(debt_path, debt.str());
  AtomicReplace(ledger_path, ledger_text, L".next");
  AtomicReplace(anchor_path, anchor_text, L".next");
  const auto ledger_readback = ReadFileExact(ledger_path, kMaxOrdinaryFile);
  const auto anchor_readback = ReadFileExact(anchor_path, kMaxOrdinaryFile);
  const Ledger parsed_readback = ParseLedger(ledger_readback);
  VerifyAnchor(anchor_readback, parsed_readback, ledger_readback);
  if (parsed_readback.revision != ledger.revision || parsed_readback.head != ledger.head ||
      SerializeLedger(parsed_readback) != ledger_text) Fail("E_STATE_READBACK");
  if (!DeleteFileW(debt_path.c_str())) Fail("E_DEBT_CLEAR");
  std::cout << BuildOutput(receipt, route, ledger, variant);
  if (!std::cout.good()) Fail("E_OUTPUT");
}

}  // namespace

int wmain(int argc, wchar_t** argv) {
  try {
    Run(argc, argv);
    return 0;
  } catch (const Failure& failure) {
    std::cerr << failure.what() << '\n';
    return 2;
  } catch (...) {
    std::cerr << "E_INTERNAL\n";
    return 3;
  }
}

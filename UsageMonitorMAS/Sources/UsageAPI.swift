import Foundation

struct LimitBucket: Decodable {
    let utilization: Double?
    let resetsAt: String?

    enum CodingKeys: String, CodingKey {
        case utilization
        case resetsAt = "resets_at"
    }
}

struct UsageResponse: Decodable {
    let fiveHour: LimitBucket?
    let sevenDay: LimitBucket?
    let sevenDaySonnet: LimitBucket?

    enum CodingKeys: String, CodingKey {
        case fiveHour = "five_hour"
        case sevenDay = "seven_day"
        case sevenDaySonnet = "seven_day_sonnet"
    }
}

enum UsageAPIError: Error {
    case unauthorized
    case http(Int)
    case network(Error)
    case invalidResponse
}

enum UsageAPI {

    static func fetch(orgId: String, cookie: String,
                      completion: @escaping (Result<UsageResponse, UsageAPIError>) -> Void) {
        guard let url = URL(string: "https://claude.ai/api/organizations/\(orgId)/usage") else {
            completion(.failure(.invalidResponse))
            return
        }

        var request = URLRequest(url: url, timeoutInterval: 10)
        request.httpShouldHandleCookies = false
        let headers: [String: String] = [
            "Cookie": cookie,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Ch-Ua": "\"Not(A:Brand\";v=\"8\", \"Chromium\";v=\"144\", \"Google Chrome\";v=\"144\"",
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": "\"macOS\"",
            "Referer": "https://claude.ai/settings/usage",
        ]
        for (key, value) in headers {
            request.setValue(value, forHTTPHeaderField: key)
        }

        URLSession.shared.dataTask(with: request) { data, response, error in
            let result: Result<UsageResponse, UsageAPIError>
            defer { DispatchQueue.main.async { completion(result) } }

            if let error {
                result = .failure(.network(error))
                return
            }
            guard let http = response as? HTTPURLResponse, let data else {
                result = .failure(.invalidResponse)
                return
            }
            switch http.statusCode {
            case 200:
                do {
                    result = .success(try JSONDecoder().decode(UsageResponse.self, from: data))
                } catch {
                    result = .failure(.invalidResponse)
                }
            case 401:
                result = .failure(.unauthorized)
            default:
                result = .failure(.http(http.statusCode))
            }
        }.resume()
    }
}

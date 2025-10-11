
using System;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

namespace UGTLive
{
    public class OpenRouterService : ITranslationService
    {
        private static readonly HttpClient client = new HttpClient();
        private const string API_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions";

        public async Task<string?> TranslateAsync(string text, string prompt)
        {
            string? apiKey = ConfigManager.Instance.GetOpenRouterApiKey();
            if (string.IsNullOrEmpty(apiKey))
            {
                Console.WriteLine("OpenRouter API key not set.");
                return null;
            }

            if (string.IsNullOrWhiteSpace(prompt))
            {
                prompt = "Respond helpfully.";
            }

            object requestBody;

            if (string.IsNullOrEmpty(text))
            {
                // Text-only request
                requestBody = new
                {
                    model = ConfigManager.Instance.GetOpenRouterModel(),
                    messages = new object[]
                    {
                        new { role = "system", content = new object[]{ new { type = "text", text = "You are a helpful assistant." } } },
                        new { role = "user", content = new object[]{ new { type = "text", text = prompt } } }
                    }
                };
            }
            else
            {
                // Multimodal request with image
                string base64Image = text;
                requestBody = new
                {
                    model = ConfigManager.Instance.GetOpenRouterModel(),
                    messages = new object[]
                    {
                        new { role = "system", content = new object[]{ new { type = "text", text = prompt } } },
                        new {
                            role = "user",
                            content = new object[]
                            {
                                new { type = "image_url", image_url = new { url = $"data:image/png;base64,{base64Image}" } }
                            }
                        }
                    }
                };
            }

            try
            {
                using (var request = new HttpRequestMessage(HttpMethod.Post, API_ENDPOINT))
                {
                    request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", apiKey);
                    request.Headers.Add("HTTP-Referer", "https://github.com/sethrobinson/ugtlive"); // Recommended by OpenRouter
                    request.Headers.Add("X-Title", "UGTLive"); // Recommended by OpenRouter

                    string jsonPayload = JsonSerializer.Serialize(requestBody);
                    request.Content = new StringContent(jsonPayload, Encoding.UTF8, "application/json");

                    HttpResponseMessage response = await client.SendAsync(request);

                    if (response.IsSuccessStatusCode)
                    {
                        string responseBody = await response.Content.ReadAsStringAsync();
                        using (JsonDocument doc = JsonDocument.Parse(responseBody))
                        {
                            JsonElement root = doc.RootElement;
                            if (root.TryGetProperty("choices", out JsonElement choices) && choices.GetArrayLength() > 0)
                            {
                                if (choices[0].TryGetProperty("message", out JsonElement message) && message.TryGetProperty("content", out JsonElement content))
                                {
                                    return content.GetString();
                                }
                            }
                        }
                        return responseBody; // Fallback
                    }
                    else
                    {
                        string errorBody = await response.Content.ReadAsStringAsync();
                        Console.WriteLine($"OpenRouter API Error: {response.StatusCode}\n{errorBody}");
                        return null;
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Exception during OpenRouter API call: {ex.Message}");
                return null;
            }
        }
    }
}

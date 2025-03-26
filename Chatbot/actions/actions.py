from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker, executor
from rasa_sdk.events import SlotSet
from utils.quantity_processcor import process_quantity

import requests

class ActionFetchTopClubs(Action):
    def name(self) -> Text:
        return "action_fetch_top_clubs"

    def run(self, dispatcher: executor.CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        try:
            quantity = self._process_quantity(tracker)
            clubs = self._fetch_clubs(quantity)
            response = self._generate_response(clubs, quantity)
            dispatcher.utter_message(text=response)
            return [SlotSet("quantity", str(quantity))]
        except Exception:
            dispatcher.utter_message(text="Xin lỗi, có lỗi khi tìm club. Vui lòng thử lại.")
            return []

    def _process_quantity(self, tracker: Tracker) -> int:
        """Validate và chuẩn hóa quantity"""
        quantity = tracker.get_slot("quantity") or process_quantity(
            tracker.latest_message.get('text', ''),
            next(tracker.get_latest_entity_values("quantity"), None))

        return max(1, min(5, int(quantity or 3)))

    def _fetch_clubs(self, quantity: int) -> List[Dict]:
        """Lấy danh sách club từ API (chỉ lấy name, rating, hotline)"""
        try:
            response = requests.get(
                f"https://bookingweb.shop/api/v1/clubs/top-club/{quantity}",
                timeout=5
            )
            response.raise_for_status()

            api_data = response.json()

            if not api_data.get("isSuccess", False):
                raise ValueError("API returned unsuccessful status")

            return [
                {
                    "name": club.get("name", "Unknown Club"),
                    "rating": float(club.get("averageRating", 0)),
                    "hotline": club.get("hotline", "N/A")
                }
                for club in api_data.get("value", [])
            ]

        except Exception as e:
            return []

    def _generate_response(self, clubs: List[Dict], quantity: int) -> str:
        """Tạo message chỉ hiển thị name, rating, hotline"""
        response = f"🏆 Top {quantity} club:\n"
        for idx, club in enumerate(clubs, 1):
            response += f"{idx}. {club['name']} (⭐️{club['rating']}) 📞{club['hotline']}\n"
        return response


    # def _get_fallback_clubs(self, quantity: int) -> List[Dict]:
    #     """Dữ liệu dự phòng đơn giản"""
    #     return [
    #                {"name": "The Champion", "rating": 4.9, "hotline": "0232921582"},
    #                {"name": "Smash Arena", "rating": 4.8, "hotline": "032921582"}
    #            ][:quantity]

    # def _fetch_clubs(self, quantity: int) -> List[Dict]:
    #     """Lấy danh sách club (mock data)"""
    #     return [
    #         {"name": "The Champion", "rating": 4.9},
    #         {"name": "Smash Arena", "rating": 4.8},
    #         {"name": "Net King", "rating": 4.7},
    #         {"name": "Racket Pro", "rating": 4.6},
    #         {"name": "Shuttle Master", "rating": 4.5}
    #     ][:quantity]

    # def _generate_response(self, clubs: List[Dict], quantity: int) -> str:
    #     """Tạo message response"""
    #     return (
    #         f"🏆 Top {quantity} club:\n" +
    #         "\n".join(f"{i}. {c['name']} (⭐️{c['rating']})"
    #                  for i, c in enumerate(clubs, 1)) +
    #         ("\nBạn muốn đặt sân ở đây không?" if quantity == 1 else "")
    #     )
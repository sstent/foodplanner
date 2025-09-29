"""
Tests for Weekly Menu operations
"""
import pytest


class TestWeeklyMenuRoutes:
    """Test weekly menu-related routes"""
    
    def test_get_weekly_menu_page(self, client):
        """Test GET /weeklymenu page"""
        response = client.get("/weeklymenu")
        assert response.status_code == 200
        assert b"Weekly" in response.content or b"weekly" in response.content or b"Menu" in response.content


class TestWeeklyMenuCRUD:
    """Test weekly menu CRUD operations"""
    
    def test_create_weekly_menu(self, client, db_session, sample_template):
        """Test creating a weekly menu"""
        from main import WeeklyMenu, WeeklyMenuDay
        
        weekly_menu = WeeklyMenu(name="Test Weekly Menu")
        db_session.add(weekly_menu)
        db_session.commit()
        db_session.refresh(weekly_menu)
        
        # Add days to weekly menu
        for day in range(7):
            menu_day = WeeklyMenuDay(
                weekly_menu_id=weekly_menu.id,
                day_of_week=day,
                template_id=sample_template.id
            )
            db_session.add(menu_day)
        
        db_session.commit()
        
        assert weekly_menu.id is not None
        assert len(weekly_menu.weekly_menu_days) == 7
    
    def test_weekly_menu_relationships(self, client, db_session, sample_template):
        """Test weekly menu relationships"""
        from main import WeeklyMenu, WeeklyMenuDay
        
        weekly_menu = WeeklyMenu(name="Relationship Test Menu")
        db_session.add(weekly_menu)
        db_session.commit()
        db_session.refresh(weekly_menu)
        
        menu_day = WeeklyMenuDay(
            weekly_menu_id=weekly_menu.id,
            day_of_week=0,  # Monday
            template_id=sample_template.id
        )
        db_session.add(menu_day)
        db_session.commit()
        
        # Verify relationships
        assert menu_day.weekly_menu.id == weekly_menu.id
        assert menu_day.template.id == sample_template.id

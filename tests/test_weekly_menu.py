"""
Tests for Weekly Menu operations
"""
import pytest


class TestWeeklyMenuRoutes:
    """Test weekly menu-related routes"""
    
    def test_get_weekly_menu_page(self, client, sample_weekly_menu, sample_template):
        """Test GET /weeklymenu page displays weekly menus correctly"""
        response = client.get("/weeklymenu")
        assert response.status_code == 200
        
        # Check for the presence of the weekly menu name
        assert sample_weekly_menu.name.encode('utf-8') in response.content
        
        # Check for the assigned templates' names
        for weekly_menu_day in sample_weekly_menu.weekly_menu_days:
            assert weekly_menu_day.template.name.encode('utf-8') in response.content


    def test_create_weekly_menu_route(self, client, sample_template):
        """Test POST /weeklymenu/create route"""
        form_data = {
            "name": "My New Weekly Menu",
            "template_assignments": f"0:{sample_template.id},1:{sample_template.id}"
        }
        response = client.post("/weeklymenu/create", data=form_data)
        assert response.status_code == 200
        assert response.json() == {"status": "success", "message": "Weekly menu created successfully"}


    def test_apply_weekly_menu_route(self, client, db_session, sample_weekly_menu):
        """Test POST /weeklymenu/{weekly_menu_id}/apply route"""
        from datetime import date, timedelta
        
        today = date.today()
        # Find Monday of current week
        week_start_date = (today - timedelta(days=today.weekday())).isoformat()

        form_data = {
            "person": "Sarah",
            "week_start_date": week_start_date,
            "confirm_overwrite": "false"
        }
        response = client.post(f"/weeklymenu/{sample_weekly_menu.id}/apply", data=form_data)
        assert response.status_code == 200
        assert response.json() == {"status": "success", "message": "Weekly menu applied successfully."}


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
            day_of_week=0, # Monday
            template_id=sample_template.id
        )
        db_session.add(menu_day)
        db_session.commit()
        
        # Verify relationships
        assert menu_day.weekly_menu.id == weekly_menu.id
        assert menu_day.template.id == sample_template.id


class TestWeeklyMenuAPI:
    """Test weekly menu API endpoints"""
    
    def test_get_weekly_menu_detail(self, client, sample_weekly_menu):
        """Test GET /weeklymenu/{id} endpoint"""
        response = client.get(f"/weeklymenu/{sample_weekly_menu.id}")
        assert response.status_code == 200
        
        data = response.json()
        assert "id" in data
        assert "name" in data
        assert "weekly_menu_days" in data
        assert data["id"] == sample_weekly_menu.id
        assert data["name"] == sample_weekly_menu.name
        
    def test_get_weekly_menus_api(self, client, sample_weekly_menu):
        """Test GET /api/weeklymenus endpoint"""
        response = client.get("/api/weeklymenus")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # Should include our sample weekly menu
        
        # Find our sample menu in the response
        sample_menu_found = False
        for menu in data:
            if menu["id"] == sample_weekly_menu.id:
                sample_menu_found = True
                assert menu["name"] == sample_weekly_menu.name
                break
        assert sample_menu_found, "Sample weekly menu should be in API response"
    
    def test_update_weekly_menu(self, client, sample_weekly_menu, sample_template):
        """Test PUT /weeklymenu/{id} endpoint"""
        form_data = {
            "name": "Updated Weekly Menu Name",
            "template_assignments": f"0:{sample_template.id},1:{sample_template.id},2:{sample_template.id}"
        }
        response = client.put(f"/weeklymenu/{sample_weekly_menu.id}", data=form_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        
        # Verify the update worked by getting the menu again
        get_response = client.get(f"/weeklymenu/{sample_weekly_menu.id}")
        assert get_response.status_code == 200
        updated_data = get_response.json()
        assert updated_data["name"] == "Updated Weekly Menu Name"
    
    def test_delete_weekly_menu(self, client, sample_weekly_menu):
        """Test DELETE /weeklymenu/{id} endpoint"""
        response = client.delete(f"/weeklymenu/{sample_weekly_menu.id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        
        # Verify the deletion worked by trying to get the menu again
        get_response = client.get(f"/weeklymenu/{sample_weekly_menu.id}")
        assert get_response.status_code == 404

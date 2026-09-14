"""Navigate the public menus, including their narrow-screen container."""
def menu(page, name):
    mobile=page.locator('.ed-mobile-menu')
    if mobile.is_visible() and mobile.get_attribute('open') is None:
        mobile.locator('summary').click()
    page.locator('.ed-menu-categories').get_by_role('button',name=name,exact=True).click()

def action(page, identifier):
    if identifier=='ed-analysis':
        if page.locator('.ed-category-menu:visible').count():
            page.keyboard.press('Escape')
        if page.locator('#ed-solve-panel').is_visible():
            page.locator('[data-physics-close]').click()
        else:
            if not page.get_by_role('navigation',name='Panel views').is_visible():
                page.get_by_role('button',name='Components',exact=True).click()
            page.get_by_role('navigation',name='Panel views').get_by_role('button',name='Solve',exact=True).click()
        return
    if identifier=='ed-open-example':
        if not page.locator('#ed-files-panel').is_visible():
            page.locator('#ed-files-reopen').click()
        page.locator('#ed-open-example').scroll_into_view_if_needed()
        if page.locator('#ed-examples').is_hidden():page.locator('#ed-open-example').click()
        return
    categories={'ed-theme':'View','ed-notation':'View','ed-fit':'View','ed-auto-labels':'View','ed-present':'View',
                'ed-help':'Help','ed-export':'File','ed-share':'File'}
    if not page.locator('#'+identifier).is_visible():menu(page,categories[identifier])
    page.locator('#'+identifier).click()

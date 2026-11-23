export const STAFF_ROLES = ['director', 'staff'];
export const MENTOR_ROLES = ['mentor'];

export function homePathFor(role) {
  return role === 'mentor' ? '/mentor' : '/staff';
}

export function isStaffRole(role) {
  return STAFF_ROLES.includes(role);
}

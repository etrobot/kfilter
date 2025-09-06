// 认证服务
export class AuthService {
  private static readonly AUTH_TOKEN_KEY = 'auth_token'
  private static readonly AUTH_TIME_KEY = 'auth_time'
  private static readonly SESSION_TIMEOUT = 180 * 24 * 60 * 60 * 1000 // 180天

  /**
   * 检查用户是否已认证
   */
  static isAuthenticated(): boolean {
    const token = sessionStorage.getItem(this.AUTH_TOKEN_KEY)
    const authTime = sessionStorage.getItem(this.AUTH_TIME_KEY)
    
    if (!token || !authTime) {
      return false
    }

    // 检查会话是否过期
    const now = Date.now()
    const authTimestamp = parseInt(authTime, 10)
    
    if (now - authTimestamp > this.SESSION_TIMEOUT) {
      this.clearAuth()
      return false
    }

    return token === 'authenticated'
  }

  /**
   * 清除认证信息
   */
  static clearAuth(): void {
    sessionStorage.removeItem(this.AUTH_TOKEN_KEY)
    sessionStorage.removeItem(this.AUTH_TIME_KEY)
  }

  /**
   * 设置认证信息
   */
  static setAuth(): void {
    sessionStorage.setItem(this.AUTH_TOKEN_KEY, 'authenticated')
    sessionStorage.setItem(this.AUTH_TIME_KEY, Date.now().toString())
  }

  /**
   * 获取剩余会话时间（毫秒）
   */
  static getRemainingSessionTime(): number {
    const authTime = sessionStorage.getItem(this.AUTH_TIME_KEY)
    if (!authTime) return 0

    const authTimestamp = parseInt(authTime, 10)
    const elapsed = Date.now() - authTimestamp
    const remaining = this.SESSION_TIMEOUT - elapsed

    return Math.max(0, remaining)
  }

  /**
   * 检查是否需要重新认证的高阶函数
   */
  static requireAuth<T extends any[]>(
    callback: (...args: T) => void | Promise<void>
  ): (...args: T) => Promise<boolean> {
    return async (...args: T): Promise<boolean> => {
      if (this.isAuthenticated()) {
        await callback(...args)
        return true
      }
      return false
    }
  }
}

// 认证状态管理Hook
export function useAuth() {
  const isAuthenticated = AuthService.isAuthenticated()
  
  const clearAuth = () => {
    AuthService.clearAuth()
  }

  const setAuth = () => {
    AuthService.setAuth()
  }

  return {
    isAuthenticated,
    clearAuth,
    setAuth,
    getRemainingTime: AuthService.getRemainingSessionTime
  }
}
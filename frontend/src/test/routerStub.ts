// vue-router stand-in for components that only read/write the URL query (useQueryParam)
import { reactive } from 'vue'

export const route = reactive({ path: '/', query: {} as Record<string, string> })
export const useRoute = () => route
const navigate = ({ query }: { query: Record<string, string> }) => {
  route.query = query
}
export const useRouter = () => ({ replace: navigate, push: navigate })

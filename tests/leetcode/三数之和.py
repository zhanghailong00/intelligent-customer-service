class Solution(object):
    def threeSum(self, nums):
        res = []
        n = len(nums)
        if n<3:
            return res 
        
        nums.sort()

        for i in range(n):
            if i > 0 and nums[i]==nums[i-1]:
                continue
            
            left = i+1
            right = n-1
            while left < right:
                total = nums[i] + nums[left] + nums[right]

                if total== 0:
                    res.append([nums[i],nums[left],nums[right]])

                    while left < right and nums[left]==nums[left+1]:
                        left += 1
                    while left < right and nums[right]==nums[right-1]:
                        right -= 1

                    left += 1
                    right -= 1

                elif total < 0:
                    left += 1

                else:
                    total > 0
                    right -= 1

        return res
    
if __name__ == "__main__":
    nums = [-1,0,1,2,-1,-4]
    print(Solution().threeSum(nums))


